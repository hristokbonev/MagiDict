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

/* Forward declarations */
static PyObject *magidict_hook_with_memo(PyObject *item, PyObject *memo);
static PyObject *magidict_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static int magidict_init(MagiDictObject *self, PyObject *args, PyObject *kwds);
static void magidict_dealloc(MagiDictObject *self);
static PyObject *magidict_getitem(MagiDictObject *self, PyObject *key);
static int magidict_setitem(MagiDictObject *self, PyObject *key, PyObject *value);
static PyObject *magidict_getattro(MagiDictObject *self, PyObject *name);
static PyObject *magidict_repr(MagiDictObject *self);

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

        if (PyDict_Update(input_dict, args) < 0)
        {
            Py_DECREF(input_dict);
            Py_DECREF(memo);
            return -1;
        }

        if (kwds != NULL && PyDict_Update(input_dict, kwds) < 0)
        {
            Py_DECREF(input_dict);
            Py_DECREF(memo);
            return -1;
        }
    }
    else
    {
        Py_INCREF(input_dict);
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
    /* Handle list/tuple of keys */
    if (PyList_Check(key) || PyTuple_Check(key))
    {
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

    /* Handle dotted string keys */
    if (PyUnicode_Check(key))
    {
        const char *key_str = PyUnicode_AsUTF8(key);
        if (key_str != NULL && strchr(key_str, '.') != NULL)
        {
            PyObject *split = PyUnicode_Split(key, PyUnicode_FromString("."), -1);
            if (split != NULL)
            {
                PyObject *result = magidict_getitem(self, split);
                Py_DECREF(split);
                return result;
            }
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

/* mget method */
static PyObject *magidict_mget(MagiDictObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *key;
    PyObject *default_value = NULL;
    int has_default = 0;

    static char *kwlist[] = {"key", "default", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O", kwlist, &key, &default_value))
    {
        return NULL;
    }

    if (default_value != NULL)
    {
        has_default = 1;
    }

    if (PyDict_Contains((PyObject *)self, key))
    {
        PyObject *value = PyDict_GetItem((PyObject *)self, key);
        if (value == Py_None && (!has_default || default_value != Py_None))
        {
            return magidict_create_protected(1, 0);
        }
        Py_INCREF(value);
        return value;
    }

    if (has_default)
    {
        Py_INCREF(default_value);
        return default_value;
    }

    return magidict_create_protected(0, 1);
}

/* disenchant method */
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
            PyObject *new_value = magidict_disenchant_recursive(value, memo);
            if (new_value == NULL)
            {
                Py_DECREF(new_dict);
                Py_DECREF(item_id);
                return NULL;
            }
            PyDict_SetItem(new_dict, key, new_value);
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

    Py_DECREF(item_id);
    Py_INCREF(item);
    return item;
}

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
    if (PyArg_ParseTuple(args, "|O", &other))
    {
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

/* Method definitions */
static PyMethodDef magidict_methods[] = {
    {"mget", (PyCFunction)magidict_mget, METH_VARARGS | METH_KEYWORDS,
     "Safe get method that returns empty MagiDict for missing keys"},
    {"mg", (PyCFunction)magidict_mget, METH_VARARGS | METH_KEYWORDS,
     "Shorthand for mget"},
    {"disenchant", (PyCFunction)magidict_disenchant, METH_NOARGS,
     "Convert MagiDict back to standard dict"},
    {"update", (PyCFunction)magidict_update, METH_VARARGS | METH_KEYWORDS,
     "Update the dictionary with hooked values"},
    {NULL, NULL, 0, NULL}};

/* Member definitions */
static PyMemberDef magidict_members[] = {
    {NULL}};

/* Mapping protocol */
static PyMappingMethods magidict_as_mapping = {
    0,                               /* mp_length */
    (binaryfunc)magidict_getitem,    /* mp_subscript */
    (objobjargproc)magidict_setitem, /* mp_ass_subscript */
};

/* Type definition */
static PyTypeObject MagiDictType = {
    PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "magidict_c.MagiDict",
    .tp_doc = "A dictionary with safe attribute access",
    .tp_basicsize = sizeof(MagiDictObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = magidict_new,
    .tp_init = (initproc)magidict_init,
    .tp_dealloc = (destructor)magidict_dealloc,
    .tp_repr = (reprfunc)magidict_repr,
    .tp_as_mapping = &magidict_as_mapping,
    .tp_getattro = (getattrofunc)magidict_getattro,
    .tp_methods = magidict_methods,
    .tp_members = magidict_members,
    .tp_base = &PyDict_Type,
};

/* Module definition */
static PyModuleDef magidictmodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "magidict_c",
    .m_doc = "MagiDict implementation in C",
    .m_size = -1,
};

/* Module initialization */
PyMODINIT_FUNC PyInit_magidict_c(void)
{
    PyObject *m;

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