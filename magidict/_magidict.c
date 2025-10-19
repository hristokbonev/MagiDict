#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "structmember.h"

/* MagiDict type object */
typedef struct
{
    PyDictObject dict;
    int from_none;
    int from_missing;
} MagiDictObject;

static PyTypeObject MagiDictType;

/* Sentinel object for missing default values */
static PyObject *_MISSING = NULL;

/* Forward declarations */
static PyObject *magidict_hook_with_memo(PyObject *item, PyObject *memo);
static PyObject *magidict_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static int magidict_init(MagiDictObject *self, PyObject *args, PyObject *kwds);
static void magidict_dealloc(MagiDictObject *self);
static PyObject *magidict_getitem(MagiDictObject *self, PyObject *key);
static int magidict_setitem(MagiDictObject *self, PyObject *key, PyObject *value);
static int magidict_delitem(MagiDictObject *self, PyObject *key);
static PyObject *magidict_getattro(MagiDictObject *self, PyObject *name);
static PyObject *magidict_repr(MagiDictObject *self);
static PyObject *magidict_richcompare(MagiDictObject *self, PyObject *other, int op);

/* Helper: Check if this is a protected MagiDict */
static int magidict_is_protected(MagiDictObject *self)
{
    return self->from_none || self->from_missing;
}

/* Helper: Raise TypeError if protected */
static int magidict_raise_if_protected(MagiDictObject *self)
{
    if (magidict_is_protected(self))
    {
        PyErr_SetString(PyExc_TypeError, "Cannot modify NoneType or missing keys.");
        return -1;
    }
    return 0;
}

/* Helper: Create an empty protected MagiDict */
static PyObject *magidict_create_protected(int from_none, int from_missing)
{
    MagiDictObject *md = (MagiDictObject *)MagiDictType.tp_alloc(&MagiDictType, 0);
    if (md == NULL)
        return NULL;

    md->from_none = from_none;
    md->from_missing = from_missing;
    return (PyObject *)md;
}

/* Hook implementation - recursively convert dicts to MagiDicts */
static PyObject *magidict_hook_with_memo(PyObject *item, PyObject *memo)
{
    if (item == NULL)
        return NULL;

    /* Check memo for circular references */
    PyObject *item_id = PyLong_FromVoidPtr(item);
    if (item_id == NULL)
        return NULL;

    PyObject *cached = PyDict_GetItem(memo, item_id);
    if (cached != NULL)
    {
        Py_DECREF(item_id);
        Py_INCREF(cached);
        return cached;
    }

    /* Already a MagiDict */
    if (PyObject_TypeCheck(item, &MagiDictType))
    {
        PyDict_SetItem(memo, item_id, item);
        Py_DECREF(item_id);
        Py_INCREF(item);
        return item;
    }

    /* Convert dict to MagiDict */
    if (PyDict_Check(item))
    {
        MagiDictObject *new_dict = (MagiDictObject *)MagiDictType.tp_alloc(&MagiDictType, 0);
        if (new_dict == NULL)
        {
            Py_DECREF(item_id);
            return NULL;
        }
        new_dict->from_none = 0;
        new_dict->from_missing = 0;

        PyDict_SetItem(memo, item_id, (PyObject *)new_dict);

        PyObject *key, *value;
        Py_ssize_t pos = 0;

        while (PyDict_Next(item, &pos, &key, &value))
        {
            PyObject *hooked_value = magidict_hook_with_memo(value, memo);
            if (hooked_value == NULL)
            {
                Py_DECREF(new_dict);
                Py_DECREF(item_id);
                return NULL;
            }

            if (PyDict_SetItem((PyObject *)new_dict, key, hooked_value) < 0)
            {
                Py_DECREF(hooked_value);
                Py_DECREF(new_dict);
                Py_DECREF(item_id);
                return NULL;
            }
            Py_DECREF(hooked_value);
        }

        Py_DECREF(item_id);
        return (PyObject *)new_dict;
    }

    /* Handle lists */
    if (PyList_Check(item))
    {
        PyDict_SetItem(memo, item_id, item);
        Py_ssize_t size = PyList_Size(item);

        for (Py_ssize_t i = 0; i < size; i++)
        {
            PyObject *elem = PyList_GetItem(item, i);
            PyObject *hooked = magidict_hook_with_memo(elem, memo);
            if (hooked == NULL)
            {
                Py_DECREF(item_id);
                return NULL;
            }
            PyList_SetItem(item, i, hooked);
        }

        Py_DECREF(item_id);
        Py_INCREF(item);
        return item;
    }

    /* Handle tuples */
    if (PyTuple_Check(item))
    {
        Py_ssize_t size = PyTuple_Size(item);
        PyObject *new_tuple = PyTuple_New(size);
        if (new_tuple == NULL)
        {
            Py_DECREF(item_id);
            return NULL;
        }

        for (Py_ssize_t i = 0; i < size; i++)
        {
            PyObject *elem = PyTuple_GetItem(item, i);
            PyObject *hooked = magidict_hook_with_memo(elem, memo);
            if (hooked == NULL)
            {
                Py_DECREF(new_tuple);
                Py_DECREF(item_id);
                return NULL;
            }
            PyTuple_SetItem(new_tuple, i, hooked);
        }

        Py_DECREF(item_id);
        return new_tuple;
    }

    /* Return item as-is for other types */
    Py_DECREF(item_id);
    Py_INCREF(item);
    return item;
}

/* __init__ method */
static int magidict_init(MagiDictObject *self, PyObject *args, PyObject *kwds)
{
    self->from_none = 0;
    self->from_missing = 0;

    PyObject *memo = PyDict_New();
    if (memo == NULL)
        return -1;

    PyObject *input_dict = NULL;

    /* Handle initialization */
    if (PyTuple_Size(args) == 1 && (kwds == NULL || PyDict_Size(kwds) == 0))
    {
        PyObject *arg = PyTuple_GetItem(args, 0);
        if (PyDict_Check(arg))
        {
            input_dict = arg;
            Py_INCREF(input_dict);
        }
    }

    if (input_dict == NULL)
    {
        input_dict = PyDict_New();
        if (input_dict == NULL)
        {
            Py_DECREF(memo);
            return -1;
        }

        if (args != NULL && PyTuple_Size(args) > 0)
        {
            PyObject *arg = PyTuple_GetItem(args, 0);
            if (PyDict_Check(arg))
            {
                if (PyDict_Update(input_dict, arg) < 0)
                {
                    Py_DECREF(input_dict);
                    Py_DECREF(memo);
                    return -1;
                }
            }
        }

        if (kwds != NULL && PyDict_Update(input_dict, kwds) < 0)
        {
            Py_DECREF(input_dict);
            Py_DECREF(memo);
            return -1;
        }
    }

    /* Add self to memo */
    PyObject *self_id = PyLong_FromVoidPtr(input_dict);
    if (self_id == NULL)
    {
        Py_DECREF(input_dict);
        Py_DECREF(memo);
        return -1;
    }
    PyDict_SetItem(memo, self_id, (PyObject *)self);
    Py_DECREF(self_id);

    /* Hook all items */
    PyObject *key, *value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(input_dict, &pos, &key, &value))
    {
        PyObject *hooked_value = magidict_hook_with_memo(value, memo);
        if (hooked_value == NULL)
        {
            Py_DECREF(input_dict);
            Py_DECREF(memo);
            return -1;
        }

        if (PyDict_SetItem((PyObject *)self, key, hooked_value) < 0)
        {
            Py_DECREF(hooked_value);
            Py_DECREF(input_dict);
            Py_DECREF(memo);
            return -1;
        }
        Py_DECREF(hooked_value);
    }

    Py_DECREF(input_dict);
    Py_DECREF(memo);
    return 0;
}

/* __new__ method */
static PyObject *magidict_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    MagiDictObject *self;
    self = (MagiDictObject *)PyDict_Type.tp_new(type, args, kwds);
    if (self != NULL)
    {
        self->from_none = 0;
        self->from_missing = 0;
    }
    return (PyObject *)self;
}

/* __dealloc__ method */
static void magidict_dealloc(MagiDictObject *self)
{
    PyDict_Type.tp_dealloc((PyObject *)self);
}

/* __getitem__ implementation */
static PyObject *magidict_getitem(MagiDictObject *self, PyObject *key)
{
    /* Handle list/tuple of keys for nested access */
    if (PyList_Check(key) || PyTuple_Check(key))
    {
        /* Check if tuple is actually a key in the dict */
        if (PyTuple_Check(key) && PyDict_Contains((PyObject *)self, key))
        {
            PyObject *value = PyDict_GetItem((PyObject *)self, key);
            if (value != NULL)
            {
                Py_INCREF(value);
                return value;
            }
        }

        PyObject *obj = (PyObject *)self;
        Py_INCREF(obj);

        Py_ssize_t size = PySequence_Size(key);
        for (Py_ssize_t i = 0; i < size; i++)
        {
            PyObject *k = PySequence_GetItem(key, i);
            if (k == NULL)
            {
                Py_DECREF(obj);
                return NULL;
            }

            /* Handle Mapping (dict-like) access */
            if (PyDict_Check(obj))
            {
                PyObject *next = PyDict_GetItem(obj, k);
                if (next == NULL)
                {
                    Py_DECREF(k);
                    Py_DECREF(obj);
                    return magidict_create_protected(0, 1);
                }
                Py_INCREF(next);
                Py_DECREF(obj);
                obj = next;
            }
            /* Handle Sequence (list-like) access */
            else if (PySequence_Check(obj) && !PyUnicode_Check(obj) && !PyBytes_Check(obj))
            {
                PyObject *index = PyNumber_Long(k);
                if (index == NULL)
                {
                    PyErr_Clear();
                    Py_DECREF(k);
                    Py_DECREF(obj);
                    return magidict_create_protected(0, 1);
                }
                long idx = PyLong_AsLong(index);
                Py_DECREF(index);

                PyObject *next = PySequence_GetItem(obj, idx);
                if (next == NULL)
                {
                    PyErr_Clear();
                    Py_DECREF(k);
                    Py_DECREF(obj);
                    return magidict_create_protected(0, 1);
                }
                Py_DECREF(obj);
                obj = next;
            }
            else
            {
                Py_DECREF(k);
                Py_DECREF(obj);
                return magidict_create_protected(0, 1);
            }
            Py_DECREF(k);
        }

        if (obj == Py_None)
        {
            Py_DECREF(obj);
            return magidict_create_protected(1, 0);
        }

        return obj;
    }

    /* Standard dict access */
    PyObject *value = PyDict_GetItem((PyObject *)self, key);
    if (value != NULL)
    {
        Py_INCREF(value);
        return value;
    }

    /* Handle dotted string keys for nested unforgiving access */
    if (PyUnicode_Check(key))
    {
        const char *key_str = PyUnicode_AsUTF8(key);
        if (key_str != NULL && strchr(key_str, '.') != NULL)
        {
            PyObject *dot = PyUnicode_FromString(".");
            if (dot == NULL)
            {
                PyErr_SetObject(PyExc_KeyError, key);
                return NULL;
            }

            PyObject *split = PyUnicode_Split(key, dot, -1);
            Py_DECREF(dot);

            if (split == NULL)
            {
                PyErr_SetObject(PyExc_KeyError, key);
                return NULL;
            }

            PyObject *obj = (PyObject *)self;
            Py_INCREF(obj);
            Py_ssize_t size = PyList_Size(split);

            for (Py_ssize_t i = 0; i < size; i++)
            {
                PyObject *k = PyList_GetItem(split, i);

                if (PyDict_Check(obj))
                {
                    PyObject *next = PyDict_GetItem(obj, k);
                    if (next == NULL)
                    {
                        Py_DECREF(obj);
                        Py_DECREF(split);
                        PyErr_SetObject(PyExc_KeyError, key);
                        return NULL;
                    }
                    Py_INCREF(next);
                    Py_DECREF(obj);
                    obj = next;
                }
                else if (PySequence_Check(obj) && !PyUnicode_Check(obj) && !PyBytes_Check(obj))
                {
                    PyObject *index = PyNumber_Long(k);
                    if (index == NULL)
                    {
                        Py_DECREF(obj);
                        Py_DECREF(split);
                        PyErr_SetObject(PyExc_KeyError, key);
                        return NULL;
                    }
                    long idx = PyLong_AsLong(index);
                    Py_DECREF(index);

                    PyObject *next = PySequence_GetItem(obj, idx);
                    if (next == NULL)
                    {
                        Py_DECREF(obj);
                        Py_DECREF(split);
                        PyErr_SetObject(PyExc_KeyError, key);
                        return NULL;
                    }
                    Py_DECREF(obj);
                    obj = next;
                }
                else
                {
                    Py_DECREF(obj);
                    Py_DECREF(split);
                    PyErr_SetObject(PyExc_KeyError, key);
                    return NULL;
                }
            }

            Py_DECREF(split);
            return obj;
        }
    }

    /* Key not found - raise KeyError */
    PyErr_SetObject(PyExc_KeyError, key);
    return NULL;
}

/* __setitem__ implementation */
static int magidict_setitem(MagiDictObject *self, PyObject *key, PyObject *value)
{
    if (magidict_raise_if_protected(self) < 0)
    {
        return -1;
    }

    if (value == NULL)
    {
        return magidict_delitem(self, key);
    }

    PyObject *memo = PyDict_New();
    if (memo == NULL)
        return -1;

    PyObject *hooked_value = magidict_hook_with_memo(value, memo);
    Py_DECREF(memo);

    if (hooked_value == NULL)
        return -1;

    int result = PyDict_SetItem((PyObject *)self, key, hooked_value);
    Py_DECREF(hooked_value);

    return result;
}

/* __delitem__ implementation */
static int magidict_delitem(MagiDictObject *self, PyObject *key)
{
    if (magidict_raise_if_protected(self) < 0)
    {
        return -1;
    }

    return PyDict_DelItem((PyObject *)self, key);
}

/* __getattribute__ implementation */
static PyObject *magidict_getattro(MagiDictObject *self, PyObject *name)
{
    /* Check for special flag attributes */
    const char *name_str = PyUnicode_AsUTF8(name);
    if (name_str != NULL)
    {
        if (strcmp(name_str, "_from_none") == 0)
        {
            return PyBool_FromLong(self->from_none);
        }
        if (strcmp(name_str, "_from_missing") == 0)
        {
            return PyBool_FromLong(self->from_missing);
        }

        /* Check if key exists in dict */
        if (PyDict_Contains((PyObject *)self, name))
        {
            PyObject *value = PyDict_GetItem((PyObject *)self, name);
            if (value == Py_None)
            {
                return magidict_create_protected(1, 0);
            }
            /* Convert dict to MagiDict if needed */
            if (PyDict_Check(value) && !PyObject_TypeCheck(value, &MagiDictType))
            {
                PyObject *memo = PyDict_New();
                if (memo == NULL)
                    return NULL;
                PyObject *hooked = magidict_hook_with_memo(value, memo);
                Py_DECREF(memo);
                if (hooked == NULL)
                    return NULL;
                PyDict_SetItem((PyObject *)self, name, hooked);
                return hooked;
            }
            Py_INCREF(value);
            return value;
        }
    }

    /* Try to get from type */
    PyObject *result = PyObject_GenericGetAttr((PyObject *)self, name);
    if (result != NULL)
    {
        return result;
    }

    /* Clear the AttributeError and return empty MagiDict */
    PyErr_Clear();
    return magidict_create_protected(0, 1);
}

/* __repr__ implementation */
static PyObject *magidict_repr(MagiDictObject *self)
{
    PyObject *dict_repr = PyDict_Type.tp_repr((PyObject *)self);
    if (dict_repr == NULL)
        return NULL;

    PyObject *result = PyUnicode_FromFormat("MagiDict(%S)", dict_repr);
    Py_DECREF(dict_repr);
    return result;
}

/* __dir__ implementation for autocomplete */
static PyObject *magidict_dir(MagiDictObject *self, PyObject *Py_UNUSED(ignored))
{
    PyObject *result = PyList_New(0);
    if (result == NULL)
        return NULL;

    /* Add string keys from dict */
    PyObject *keys = PyDict_Keys((PyObject *)self);
    if (keys != NULL)
    {
        Py_ssize_t size = PyList_Size(keys);
        for (Py_ssize_t i = 0; i < size; i++)
        {
            PyObject *key = PyList_GetItem(keys, i);
            if (PyUnicode_Check(key))
            {
                PyList_Append(result, key);
            }
        }
        Py_DECREF(keys);
    }

    /* Add class attributes */
    PyObject *type_dict = ((PyTypeObject *)Py_TYPE(self))->tp_dict;
    if (type_dict != NULL)
    {
        PyObject *type_keys = PyDict_Keys(type_dict);
        if (type_keys != NULL)
        {
            Py_ssize_t size = PyList_Size(type_keys);
            for (Py_ssize_t i = 0; i < size; i++)
            {
                PyObject *key = PyList_GetItem(type_keys, i);
                if (PySequence_Contains(result, key) != 1)
                {
                    PyList_Append(result, key);
                }
            }
            Py_DECREF(type_keys);
        }
    }

    /* Sort the list */
    if (PyList_Sort(result) < 0)
    {
        Py_DECREF(result);
        return NULL;
    }

    return result;
}

/* __richcompare__ implementation */
static PyObject *magidict_richcompare(MagiDictObject *self, PyObject *other, int op)
{
    return PyDict_Type.tp_richcompare((PyObject *)self, other, op);
}

/* mget method */
static PyObject *magidict_mget(MagiDictObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *key;
    PyObject *default_value = _MISSING;

    static char *kwlist[] = {"key", "default", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O", kwlist, &key, &default_value))
    {
        return NULL;
    }

    if (default_value == _MISSING)
    {
        default_value = magidict_create_protected(0, 1);
        if (default_value == NULL)
            return NULL;
    }
    else
    {
        Py_INCREF(default_value);
    }

    if (PyDict_Contains((PyObject *)self, key))
    {
        PyObject *value = PyDict_GetItem((PyObject *)self, key);
        if (value == Py_None && default_value != Py_None)
        {
            Py_DECREF(default_value);
            return magidict_create_protected(1, 0);
        }
        Py_DECREF(default_value);
        Py_INCREF(value);
        return value;
    }

    return default_value;
}

/* strict_get method */
static PyObject *magidict_strict_get(MagiDictObject *self, PyObject *key)
{
    PyObject *value = PyDict_GetItem((PyObject *)self, key);
    if (value == NULL)
    {
        PyErr_SetObject(PyExc_KeyError, key);
        return NULL;
    }
    Py_INCREF(value);
    return value;
}

/* disenchant helper */
static PyObject *magidict_disenchant_recursive(PyObject *item, PyObject *memo);

static PyObject *magidict_disenchant_recursive(PyObject *item, PyObject *memo)
{
    PyObject *item_id = PyLong_FromVoidPtr(item);
    if (item_id == NULL)
        return NULL;

    PyObject *cached = PyDict_GetItem(memo, item_id);
    if (cached != NULL)
    {
        Py_DECREF(item_id);
        Py_INCREF(cached);
        return cached;
    }

    if (PyObject_TypeCheck(item, &MagiDictType) || PyDict_Check(item))
    {
        PyObject *new_dict = PyDict_New();
        if (new_dict == NULL)
        {
            Py_DECREF(item_id);
            return NULL;
        }

        PyDict_SetItem(memo, item_id, new_dict);

        PyObject *key, *value;
        Py_ssize_t pos = 0;

        while (PyDict_Next(item, &pos, &key, &value))
        {
            PyObject *new_key = magidict_disenchant_recursive(key, memo);
            if (new_key == NULL)
            {
                Py_DECREF(new_dict);
                Py_DECREF(item_id);
                return NULL;
            }
            PyObject *new_value = magidict_disenchant_recursive(value, memo);
            if (new_value == NULL)
            {
                Py_DECREF(new_key);
                Py_DECREF(new_dict);
                Py_DECREF(item_id);
                return NULL;
            }
            PyDict_SetItem(new_dict, new_key, new_value);
            Py_DECREF(new_key);
            Py_DECREF(new_value);
        }

        Py_DECREF(item_id);
        return new_dict;
    }

    if (PyList_Check(item))
    {
        Py_ssize_t size = PyList_Size(item);
        PyObject *new_list = PyList_New(size);
        if (new_list == NULL)
        {
            Py_DECREF(item_id);
            return NULL;
        }

        PyDict_SetItem(memo, item_id, new_list);

        for (Py_ssize_t i = 0; i < size; i++)
        {
            PyObject *elem = PyList_GetItem(item, i);
            PyObject *new_elem = magidict_disenchant_recursive(elem, memo);
            if (new_elem == NULL)
            {
                Py_DECREF(new_list);
                Py_DECREF(item_id);
                return NULL;
            }
            PyList_SetItem(new_list, i, new_elem);
        }

        Py_DECREF(item_id);
        return new_list;
    }

    if (PyTuple_Check(item))
    {
        Py_ssize_t size = PyTuple_Size(item);
        PyObject *new_tuple = PyTuple_New(size);
        if (new_tuple == NULL)
        {
            Py_DECREF(item_id);
            return NULL;
        }

        for (Py_ssize_t i = 0; i < size; i++)
        {
            PyObject *elem = PyTuple_GetItem(item, i);
            PyObject *new_elem = magidict_disenchant_recursive(elem, memo);
            if (new_elem == NULL)
            {
                Py_DECREF(new_tuple);
                Py_DECREF(item_id);
                return NULL;
            }
            PyTuple_SetItem(new_tuple, i, new_elem);
        }

        Py_DECREF(item_id);
        return new_tuple;
    }

    if (PySet_Check(item) || PyFrozenSet_Check(item))
    {
        PyObject *new_set = PySet_New(NULL);
        if (new_set == NULL)
        {
            Py_DECREF(item_id);
            return NULL;
        }

        PyObject *iterator = PyObject_GetIter(item);
        if (iterator == NULL)
        {
            Py_DECREF(new_set);
            Py_DECREF(item_id);
            return NULL;
        }

        PyObject *elem;
        while ((elem = PyIter_Next(iterator)) != NULL)
        {
            PyObject *new_elem = magidict_disenchant_recursive(elem, memo);
            Py_DECREF(elem);
            if (new_elem == NULL)
            {
                Py_DECREF(iterator);
                Py_DECREF(new_set);
                Py_DECREF(item_id);
                return NULL;
            }
            PySet_Add(new_set, new_elem);
            Py_DECREF(new_elem);
        }
        Py_DECREF(iterator);

        if (PyFrozenSet_Check(item))
        {
            PyObject *frozen = PyFrozenSet_New(new_set);
            Py_DECREF(new_set);
            Py_DECREF(item_id);
            return frozen;
        }

        Py_DECREF(item_id);
        return new_set;
    }

    Py_DECREF(item_id);
    Py_INCREF(item);
    return item;
}

/* disenchant method */
static PyObject *magidict_disenchant(MagiDictObject *self, PyObject *Py_UNUSED(ignored))
{
    PyObject *memo = PyDict_New();
    if (memo == NULL)
        return NULL;

    PyObject *result = magidict_disenchant_recursive((PyObject *)self, memo);
    Py_DECREF(memo);

    return result;
}

/* update method */
static PyObject *magidict_update(MagiDictObject *self, PyObject *args, PyObject *kwds)
{
    if (magidict_raise_if_protected(self) < 0)
    {
        return NULL;
    }

    PyObject *other = NULL;
    if (PyTuple_Size(args) > 0)
    {
        other = PyTuple_GetItem(args, 0);
    }

    if (other != NULL && PyDict_Check(other))
    {
        PyObject *key, *value;
        Py_ssize_t pos = 0;

        while (PyDict_Next(other, &pos, &key, &value))
        {
            if (magidict_setitem(self, key, value) < 0)
            {
                return NULL;
            }
        }
    }

    if (kwds != NULL)
    {
        PyObject *key, *value;
        Py_ssize_t pos = 0;

        while (PyDict_Next(kwds, &pos, &key, &value))
        {
            if (magidict_setitem(self, key, value) < 0)
            {
                return NULL;
            }
        }
    }

    Py_RETURN_NONE;
}

/* copy method */
static PyObject *magidict_copy(MagiDictObject *self, PyObject *Py_UNUSED(ignored))
{
    PyObject *dict_copy = PyDict_Copy((PyObject *)self);
    if (dict_copy == NULL)
        return NULL;

    MagiDictObject *new_copy = (MagiDictObject *)PyObject_CallFunctionObjArgs(
        (PyObject *)&MagiDictType, dict_copy, NULL);
    Py_DECREF(dict_copy);

    if (new_copy == NULL)
        return NULL;

    /* Preserve flags */
    new_copy->from_none = self->from_none;
    new_copy->from_missing = self->from_missing;

    return (PyObject *)new_copy;
}

/* setdefault method */
static PyObject *magidict_setdefault(MagiDictObject *self, PyObject *args)
{
    if (magidict_raise_if_protected(self) < 0)
    {
        return NULL;
    }

    PyObject *key, *default_value = Py_None;
    if (!PyArg_ParseTuple(args, "O|O", &key, &default_value))
    {
        return NULL;
    }

    if (PyDict_Contains((PyObject *)self, key))
    {
        PyObject *value = PyDict_GetItem((PyObject *)self, key);
        Py_INCREF(value);
        return value;
    }

    PyObject *memo = PyDict_New();
    if (memo == NULL)
        return NULL;

    PyObject *hooked_value = magidict_hook_with_memo(default_value, memo);
    Py_DECREF(memo);

    if (hooked_value == NULL)
        return NULL;

    if (PyDict_SetItem((PyObject *)self, key, hooked_value) < 0)
    {
        Py_DECREF(hooked_value);
        return NULL;
    }

    return hooked_value;
}

/* fromkeys classmethod */
static PyObject *magidict_fromkeys(PyTypeObject *type, PyObject *args)
{
    PyObject *seq, *value = Py_None;
    if (!PyArg_ParseTuple(args, "O|O", &seq, &value))
    {
        return NULL;
    }

    PyObject *d = PyDict_New();
    if (d == NULL)
        return NULL;

    PyObject *memo = PyDict_New();
    if (memo == NULL)
    {
        Py_DECREF(d);
        return NULL;
    }

    PyObject *hooked_value = magidict_hook_with_memo(value, memo);
    Py_DECREF(memo);

    if (hooked_value == NULL)
    {
        Py_DECREF(d);
        return NULL;
    }

    PyObject *iterator = PyObject_GetIter(seq);
    if (iterator == NULL)
    {
        Py_DECREF(hooked_value);
        Py_DECREF(d);
        return NULL;
    }

    PyObject *key;
    while ((key = PyIter_Next(iterator)) != NULL)
    {
        PyDict_SetItem(d, key, hooked_value);
        Py_DECREF(key);
    }
    Py_DECREF(iterator);
    Py_DECREF(hooked_value);

    PyObject *result = PyObject_CallFunctionObjArgs((PyObject *)type, d, NULL);
    Py_DECREF(d);

    return result;
}

/* pop method */
static PyObject *magidict_pop(MagiDictObject *self, PyObject *args)
{
    if (magidict_raise_if_protected(self) < 0)
    {
        return NULL;
    }

    return PyDict_Type.tp_methods[0].ml_meth((PyObject *)self, args);
}

/* popitem method */
static PyObject *magidict_popitem(MagiDictObject *self, PyObject *Py_UNUSED(ignored))
{
    if (magidict_raise_if_protected(self) < 0)
    {
        return NULL;
    }

    PyObject *key, *value;
    Py_ssize_t pos = 0;

    if (!PyDict_Next((PyObject *)self, &pos, &key, &value))
    {
        PyErr_SetString(PyExc_KeyError, "dictionary is empty");
        return NULL;
    }

    PyObject *result = PyTuple_Pack(2, key, value);
    if (result == NULL)
        return NULL;

    if (PyDict_DelItem((PyObject *)self, key) < 0)
    {
        Py_DECREF(result);
        return NULL;
    }

    return result;
}

/* clear method */
static PyObject *magidict_clear(MagiDictObject *self, PyObject *Py_UNUSED(ignored))
{
    if (magidict_raise_if_protected(self) < 0)
    {
        return NULL;
    }

    PyDict_Clear((PyObject *)self);
    Py_RETURN_NONE;
}

/* search_key method */
static PyObject *magidict_search_key_recursive(PyObject *obj, PyObject *key, PyObject *default_val);

static PyObject *magidict_search_key_recursive(PyObject *obj, PyObject *key, PyObject *default_val)
{
    if (PyObject_TypeCheck(obj, &MagiDictType) || PyDict_Check(obj))
    {
        PyObject *dict_key, *value;
        Py_ssize_t pos = 0;

        while (PyDict_Next(obj, &pos, &dict_key, &value))
        {
            int cmp = PyObject_RichCompareBool(dict_key, key, Py_EQ);
            if (cmp < 0)
                return NULL;
            if (cmp == 1)
            {
                Py_INCREF(value);
                return value;
            }

            if (PyDict_Check(value) || PyObject_TypeCheck(value, &MagiDictType))
            {
                PyObject *result = magidict_search_key_recursive(value, key, default_val);
                if (result != default_val)
                {
                    return result;
                }
                Py_DECREF(result);
            }
            else if (PySequence_Check(value) && !PyUnicode_Check(value) && !PyBytes_Check(value))
            {
                Py_ssize_t size = PySequence_Size(value);
                for (Py_ssize_t i = 0; i < size; i++)
                {
                    PyObject *item = PySequence_GetItem(value, i);
                    if (item == NULL)
                        continue;

                    if (PyDict_Check(item) || PyObject_TypeCheck(item, &MagiDictType))
                    {
                        PyObject *result = magidict_search_key_recursive(item, key, default_val);
                        Py_DECREF(item);
                        if (result != default_val)
                        {
                            return result;
                        }
                        Py_DECREF(result);
                    }
                    else
                    {
                        Py_DECREF(item);
                    }
                }
            }
        }
    }

    Py_INCREF(default_val);
    return default_val;
}

static PyObject *magidict_search_key(MagiDictObject *self, PyObject *args)
{
    PyObject *key, *default_val = Py_None;
    if (!PyArg_ParseTuple(args, "O|O", &key, &default_val))
    {
        return NULL;
    }

    return magidict_search_key_recursive((PyObject *)self, key, default_val);
}

/* search_keys method */
static void magidict_search_keys_recursive(PyObject *obj, PyObject *key, PyObject *results);

static void magidict_search_keys_recursive(PyObject *obj, PyObject *key, PyObject *results)
{
    if (PyObject_TypeCheck(obj, &MagiDictType) || PyDict_Check(obj))
    {
        PyObject *dict_key, *value;
        Py_ssize_t pos = 0;

        while (PyDict_Next(obj, &pos, &dict_key, &value))
        {
            int cmp = PyObject_RichCompareBool(dict_key, key, Py_EQ);
            if (cmp == 1)
            {
                PyList_Append(results, value);
            }

            if (PyDict_Check(value) || PyObject_TypeCheck(value, &MagiDictType))
            {
                magidict_search_keys_recursive(value, key, results);
            }
            else if (PySequence_Check(value) && !PyUnicode_Check(value) && !PyBytes_Check(value))
            {
                Py_ssize_t size = PySequence_Size(value);
                for (Py_ssize_t i = 0; i < size; i++)
                {
                    PyObject *item = PySequence_GetItem(value, i);
                    if (item == NULL)
                        continue;

                    if (PyDict_Check(item) || PyObject_TypeCheck(item, &MagiDictType))
                    {
                        magidict_search_keys_recursive(item, key, results);
                    }
                    Py_DECREF(item);
                }
            }
        }
    }
}

static PyObject *magidict_search_keys(MagiDictObject *self, PyObject *key)
{
    PyObject *results = PyList_New(0);
    if (results == NULL)
        return NULL;

    magidict_search_keys_recursive((PyObject *)self, key, results);

    return results;
}

/* __deepcopy__ implementation */
static PyObject *magidict_deepcopy_recursive(PyObject *item, PyObject *memo);

static PyObject *magidict_deepcopy_recursive(PyObject *item, PyObject *memo)
{
    PyObject *item_id = PyLong_FromVoidPtr(item);
    if (item_id == NULL)
        return NULL;

    PyObject *cached = PyDict_GetItem(memo, item_id);
    if (cached != NULL)
    {
        Py_DECREF(item_id);
        Py_INCREF(cached);
        return cached;
    }

    if (PyObject_TypeCheck(item, &MagiDictType))
    {
        MagiDictObject *src = (MagiDictObject *)item;
        MagiDictObject *copied = (MagiDictObject *)MagiDictType.tp_alloc(&MagiDictType, 0);
        if (copied == NULL)
        {
            Py_DECREF(item_id);
            return NULL;
        }

        copied->from_none = src->from_none;
        copied->from_missing = src->from_missing;

        PyDict_SetItem(memo, item_id, (PyObject *)copied);

        PyObject *key, *value;
        Py_ssize_t pos = 0;

        while (PyDict_Next((PyObject *)src, &pos, &key, &value))
        {
            PyObject *new_value = magidict_deepcopy_recursive(value, memo);
            if (new_value == NULL)
            {
                Py_DECREF(copied);
                Py_DECREF(item_id);
                return NULL;
            }
            PyDict_SetItem((PyObject *)copied, key, new_value);
            Py_DECREF(new_value);
        }

        Py_DECREF(item_id);
        return (PyObject *)copied;
    }

    /* For other types, use standard deepcopy */
    PyObject *copy_module = PyImport_ImportModule("copy");
    if (copy_module == NULL)
    {
        Py_DECREF(item_id);
        return NULL;
    }

    PyObject *deepcopy_func = PyObject_GetAttrString(copy_module, "deepcopy");
    Py_DECREF(copy_module);

    if (deepcopy_func == NULL)
    {
        Py_DECREF(item_id);
        return NULL;
    }

    PyObject *result = PyObject_CallFunctionObjArgs(deepcopy_func, item, memo, NULL);
    Py_DECREF(deepcopy_func);
    Py_DECREF(item_id);

    return result;
}

static PyObject *magidict_deepcopy(MagiDictObject *self, PyObject *args)
{
    PyObject *memo;
    if (!PyArg_ParseTuple(args, "O!", &PyDict_Type, &memo))
    {
        return NULL;
    }

    return magidict_deepcopy_recursive((PyObject *)self, memo);
}

/* __getstate__ for pickling */
static PyObject *magidict_getstate(MagiDictObject *self, PyObject *Py_UNUSED(ignored))
{
    PyObject *state = PyDict_New();
    if (state == NULL)
        return NULL;

    PyObject *data = PyDict_Copy((PyObject *)self);
    if (data == NULL)
    {
        Py_DECREF(state);
        return NULL;
    }

    PyDict_SetItemString(state, "data", data);
    Py_DECREF(data);

    PyObject *from_none = PyBool_FromLong(self->from_none);
    PyDict_SetItemString(state, "_from_none", from_none);
    Py_DECREF(from_none);

    PyObject *from_missing = PyBool_FromLong(self->from_missing);
    PyDict_SetItemString(state, "_from_missing", from_missing);
    Py_DECREF(from_missing);

    return state;
}

/* __setstate__ for pickling */
static PyObject *magidict_setstate(MagiDictObject *self, PyObject *state)
{
    PyObject *from_none = PyDict_GetItemString(state, "_from_none");
    if (from_none != NULL && PyObject_IsTrue(from_none))
    {
        self->from_none = 1;
    }

    PyObject *from_missing = PyDict_GetItemString(state, "_from_missing");
    if (from_missing != NULL && PyObject_IsTrue(from_missing))
    {
        self->from_missing = 1;
    }

    PyObject *data = PyDict_GetItemString(state, "data");
    if (data != NULL && PyDict_Check(data))
    {
        PyObject *key, *value;
        Py_ssize_t pos = 0;

        PyObject *memo = PyDict_New();
        if (memo == NULL)
            return NULL;

        while (PyDict_Next(data, &pos, &key, &value))
        {
            PyObject *hooked_value = magidict_hook_with_memo(value, memo);
            if (hooked_value == NULL)
            {
                Py_DECREF(memo);
                return NULL;
            }
            PyDict_SetItem((PyObject *)self, key, hooked_value);
            Py_DECREF(hooked_value);
        }

        Py_DECREF(memo);
    }

    Py_RETURN_NONE;
}

/* __reduce_ex__ for pickling */
static PyObject *magidict_reduce_ex(MagiDictObject *self, PyObject *protocol)
{
    PyObject *state = magidict_getstate(self, NULL);
    if (state == NULL)
        return NULL;

    PyObject *result = PyTuple_Pack(
        5,
        (PyObject *)&MagiDictType,
        PyTuple_New(0),
        state,
        Py_None,
        Py_None);

    Py_DECREF(state);
    return result;
}

/* filter method - complex implementation */
static PyObject *magidict_filter(MagiDictObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *function = Py_None;
    int drop_empty = 0;

    static char *kwlist[] = {"function", "drop_empty", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|Oi", kwlist, &function, &drop_empty))
    {
        return NULL;
    }

    /* Create lambda that checks for not None if no function provided */
    if (function == Py_None)
    {
        PyObject *lambda_str = PyUnicode_FromString("lambda x: x is not None");
        PyObject *compile_result = Py_CompileString(PyUnicode_AsUTF8(lambda_str), "<string>", Py_eval_input);
        Py_DECREF(lambda_str);
        if (compile_result == NULL)
            return NULL;

        PyObject *globals = PyDict_New();
        PyObject *locals = PyDict_New();
        function = PyEval_EvalCode(compile_result, globals, locals);
        Py_DECREF(compile_result);
        Py_DECREF(globals);
        Py_DECREF(locals);

        if (function == NULL)
            return NULL;
    }
    else
    {
        Py_INCREF(function);
    }

    MagiDictObject *filtered = (MagiDictObject *)MagiDictType.tp_alloc(&MagiDictType, 0);
    if (filtered == NULL)
    {
        Py_DECREF(function);
        return NULL;
    }
    filtered->from_none = 0;
    filtered->from_missing = 0;

    /* Determine number of args function accepts */
    PyObject *inspect_module = PyImport_ImportModule("inspect");
    if (inspect_module == NULL)
    {
        Py_DECREF(function);
        Py_DECREF(filtered);
        return NULL;
    }

    PyObject *signature_func = PyObject_GetAttrString(inspect_module, "signature");
    Py_DECREF(inspect_module);

    int num_args = 1;
    if (signature_func != NULL)
    {
        PyObject *sig = PyObject_CallFunctionObjArgs(signature_func, function, NULL);
        Py_DECREF(signature_func);

        if (sig != NULL)
        {
            PyObject *params = PyObject_GetAttrString(sig, "parameters");
            Py_DECREF(sig);
            if (params != NULL)
            {
                num_args = PyDict_Size(params);
                Py_DECREF(params);
            }
        }
        else
        {
            PyErr_Clear();
        }
    }

    /* Filter items */
    PyObject *key, *value;
    Py_ssize_t pos = 0;

    while (PyDict_Next((PyObject *)self, &pos, &key, &value))
    {
        PyObject *result;
        if (num_args == 2)
        {
            result = PyObject_CallFunctionObjArgs(function, key, value, NULL);
        }
        else
        {
            result = PyObject_CallFunctionObjArgs(function, value, NULL);
        }

        if (result == NULL)
        {
            Py_DECREF(function);
            Py_DECREF(filtered);
            return NULL;
        }

        int is_true = PyObject_IsTrue(result);
        Py_DECREF(result);

        if (is_true)
        {
            PyDict_SetItem((PyObject *)filtered, key, value);
        }
    }

    Py_DECREF(function);
    return (PyObject *)filtered;
}

/* Method definitions */
static PyMethodDef magidict_methods[] = {
    {"mget", (PyCFunction)magidict_mget, METH_VARARGS | METH_KEYWORDS,
     "Safe get method that returns empty MagiDict for missing keys"},
    {"mg", (PyCFunction)magidict_mget, METH_VARARGS | METH_KEYWORDS,
     "Shorthand for mget"},
    {"strict_get", (PyCFunction)magidict_strict_get, METH_O,
     "Strict get method that raises KeyError for missing keys"},
    {"sget", (PyCFunction)magidict_strict_get, METH_O,
     "Shorthand for strict_get"},
    {"sg", (PyCFunction)magidict_strict_get, METH_O,
     "Shorthand for strict_get"},
    {"disenchant", (PyCFunction)magidict_disenchant, METH_NOARGS,
     "Convert MagiDict back to standard dict"},
    {"update", (PyCFunction)magidict_update, METH_VARARGS | METH_KEYWORDS,
     "Update the dictionary with hooked values"},
    {"copy", (PyCFunction)magidict_copy, METH_NOARGS,
     "Return a shallow copy of the MagiDict"},
    {"setdefault", (PyCFunction)magidict_setdefault, METH_VARARGS,
     "Set default value for key if not present"},
    {"fromkeys", (PyCFunction)magidict_fromkeys, METH_VARARGS | METH_CLASS,
     "Create a new MagiDict from keys with default value"},
    {"pop", (PyCFunction)magidict_pop, METH_VARARGS,
     "Remove and return value for key"},
    {"popitem", (PyCFunction)magidict_popitem, METH_NOARGS,
     "Remove and return an arbitrary (key, value) pair"},
    {"clear", (PyCFunction)magidict_clear, METH_NOARGS,
     "Remove all items from the MagiDict"},
    {"search_key", (PyCFunction)magidict_search_key, METH_VARARGS,
     "Recursively search for a key"},
    {"search_keys", (PyCFunction)magidict_search_keys, METH_O,
     "Recursively search for all occurrences of a key"},
    {"filter", (PyCFunction)magidict_filter, METH_VARARGS | METH_KEYWORDS,
     "Filter the MagiDict based on a function"},
    {"__deepcopy__", (PyCFunction)magidict_deepcopy, METH_VARARGS,
     "Deep copy support"},
    {"__getstate__", (PyCFunction)magidict_getstate, METH_NOARGS,
     "Get state for pickling"},
    {"__setstate__", (PyCFunction)magidict_setstate, METH_O,
     "Set state for unpickling"},
    {"__reduce_ex__", (PyCFunction)magidict_reduce_ex, METH_O,
     "Reduce for pickling"},
    {"__dir__", (PyCFunction)magidict_dir, METH_NOARGS,
     "Return list of attributes for autocomplete"},
    {NULL, NULL, 0, NULL}};

/* Mapping protocol */
static PyMappingMethods magidict_as_mapping = {
    0,                               /* mp_length */
    (binaryfunc)magidict_getitem,    /* mp_subscript */
    (objobjargproc)magidict_setitem, /* mp_ass_subscript */
};

/* Type definition */
static PyTypeObject MagiDictType = {
    PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "magidict.MagiDict",
    .tp_doc = PyDoc_STR("A dictionary with safe attribute access and recursive conversion"),
    .tp_basicsize = sizeof(MagiDictObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = magidict_new,
    .tp_init = (initproc)magidict_init,
    .tp_dealloc = (destructor)magidict_dealloc,
    .tp_repr = (reprfunc)magidict_repr,
    .tp_as_mapping = &magidict_as_mapping,
    .tp_getattro = (getattrofunc)magidict_getattro,
    .tp_richcompare = (richcmpfunc)magidict_richcompare,
    .tp_methods = magidict_methods,
    .tp_base = &PyDict_Type,
};

/* Module-level functions */

/* enchant function */
static PyObject *module_enchant(PyObject *self, PyObject *d)
{
    if (PyObject_TypeCheck(d, &MagiDictType))
    {
        Py_INCREF(d);
        return d;
    }

    if (!PyDict_Check(d))
    {
        PyErr_Format(PyExc_TypeError, "Expected dict, got %s", Py_TYPE(d)->tp_name);
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)&MagiDictType, d, NULL);
}

/* none function */
static PyObject *module_none(PyObject *self, PyObject *obj)
{
    if (PyObject_TypeCheck(obj, &MagiDictType))
    {
        MagiDictObject *md = (MagiDictObject *)obj;
        if (PyDict_Size((PyObject *)md) == 0 && (md->from_none || md->from_missing))
        {
            Py_RETURN_NONE;
        }
    }

    Py_INCREF(obj);
    return obj;
}

/* magi_loads function */
static PyObject *module_magi_loads(PyObject *self, PyObject *args, PyObject *kwds)
{
    const char *json_str;

    static char *kwlist[] = {"s", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "s", kwlist, &json_str))
    {
        return NULL;
    }

    PyObject *json_module = PyImport_ImportModule("json");
    if (json_module == NULL)
        return NULL;

    PyObject *loads_func = PyObject_GetAttrString(json_module, "loads");
    Py_DECREF(json_module);

    if (loads_func == NULL)
        return NULL;

    PyObject *json_str_obj = PyUnicode_FromString(json_str);
    if (json_str_obj == NULL)
    {
        Py_DECREF(loads_func);
        return NULL;
    }

    PyObject *kwargs = PyDict_New();
    PyDict_SetItemString(kwargs, "object_hook", (PyObject *)&MagiDictType);

    PyObject *result = PyObject_Call(loads_func, PyTuple_Pack(1, json_str_obj), kwargs);

    Py_DECREF(loads_func);
    Py_DECREF(json_str_obj);
    Py_DECREF(kwargs);

    return result;
}

/* magi_load function */
static PyObject *module_magi_load(PyObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *fp;

    static char *kwlist[] = {"fp", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O", kwlist, &fp))
    {
        return NULL;
    }

    PyObject *json_module = PyImport_ImportModule("json");
    if (json_module == NULL)
        return NULL;

    PyObject *load_func = PyObject_GetAttrString(json_module, "load");
    Py_DECREF(json_module);

    if (load_func == NULL)
        return NULL;

    PyObject *kwargs = PyDict_New();
    PyDict_SetItemString(kwargs, "object_hook", (PyObject *)&MagiDictType);

    PyObject *result = PyObject_Call(load_func, PyTuple_Pack(1, fp), kwargs);

    Py_DECREF(load_func);
    Py_DECREF(kwargs);

    return result;
}

/* Module method definitions */
static PyMethodDef module_methods[] = {
    {"enchant", (PyCFunction)module_enchant, METH_O,
     "Convert a standard dictionary into a MagiDict"},
    {"none", (PyCFunction)module_none, METH_O,
     "Convert empty protected MagiDict to None"},
    {"magi_loads", (PyCFunction)module_magi_loads, METH_VARARGS | METH_KEYWORDS,
     "Deserialize JSON string into MagiDict"},
    {"magi_load", (PyCFunction)module_magi_load, METH_VARARGS | METH_KEYWORDS,
     "Deserialize JSON file into MagiDict"},
    {NULL, NULL, 0, NULL}};

/* Module definition */
static PyModuleDef magidictmodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "magidict",
    .m_doc = PyDoc_STR("MagiDict - A recursive dictionary with safe attribute access"),
    .m_size = -1,
    .m_methods = module_methods,
};

/* Module initialization */
PyMODINIT_FUNC PyInit_magidict(void)
{
    PyObject *m;

    /* Create sentinel object */
    _MISSING = PyUnicode_FromString("_MISSING_SENTINEL");
    if (_MISSING == NULL)
        return NULL;

    if (PyType_Ready(&MagiDictType) < 0)
        return NULL;

    m = PyModule_Create(&magidictmodule);
    if (m == NULL)
        return NULL;

    Py_INCREF(&MagiDictType);
    if (PyModule_AddObject(m, "MagiDict", (PyObject *)&MagiDictType) < 0)
    {
        Py_DECREF(&MagiDictType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}