#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *fast_hook_with_memo(PyObject *item, PyObject *memo, PyObject *magidict_class);

static PyObject *fast_hook_with_memo(PyObject *item, PyObject *memo, PyObject *magidict_class)
{
    if (item == NULL)
        return NULL;

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

    int is_magidict = PyObject_IsInstance(item, magidict_class);
    if (is_magidict < 0)
    {
        Py_DECREF(item_id);
        return NULL;
    }
    if (is_magidict)
    {
        PyDict_SetItem(memo, item_id, item);
        Py_DECREF(item_id);
        Py_INCREF(item);
        return item;
    }

    if (PyDict_Check(item))
    {
        PyObject *new_dict = PyObject_CallFunctionObjArgs(magidict_class, NULL);
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
            PyObject *hooked_value = fast_hook_with_memo(value, memo, magidict_class);
            if (hooked_value == NULL)
            {
                Py_DECREF(new_dict);
                Py_DECREF(item_id);
                return NULL;
            }

            if (PyDict_SetItem(new_dict, key, hooked_value) < 0)
            {
                Py_DECREF(hooked_value);
                Py_DECREF(new_dict);
                Py_DECREF(item_id);
                return NULL;
            }
            Py_DECREF(hooked_value);
        }

        Py_DECREF(item_id);
        return new_dict;
    }

    if (PyList_Check(item))
    {
        PyDict_SetItem(memo, item_id, item);
        Py_ssize_t size = PyList_Size(item);

        for (Py_ssize_t i = 0; i < size; i++)
        {
            PyObject *elem = PyList_GetItem(item, i);
            PyObject *hooked = fast_hook_with_memo(elem, memo, magidict_class);
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

    if (PyTuple_Check(item))
    {
        Py_ssize_t size = PyTuple_Size(item);
        PyObject *hooked_values = PyTuple_New(size);
        if (hooked_values == NULL)
        {
            Py_DECREF(item_id);
            return NULL;
        }

        for (Py_ssize_t i = 0; i < size; i++)
        {
            PyObject *elem = PyTuple_GetItem(item, i);
            PyObject *hooked = fast_hook_with_memo(elem, memo, magidict_class);
            if (hooked == NULL)
            {
                Py_DECREF(hooked_values);
                Py_DECREF(item_id);
                return NULL;
            }
            PyTuple_SetItem(hooked_values, i, hooked);
        }

        PyTypeObject *item_type = Py_TYPE(item);
        PyTypeObject *tuple_type = &PyTuple_Type;

        PyObject *result;
        if (item_type == tuple_type)
        {
            result = hooked_values;
        }
        else
        {
            PyObject *fields = PyObject_GetAttrString(item, "_fields");
            if (fields != NULL)
            {
                Py_DECREF(fields);
                result = PyObject_CallObject((PyObject *)item_type, hooked_values);
                Py_DECREF(hooked_values);
            }
            else
            {
                PyErr_Clear();

                PyObject *args = PyTuple_Pack(1, hooked_values);
                if (args == NULL)
                {
                    Py_DECREF(hooked_values);
                    Py_DECREF(item_id);
                    return NULL;
                }

                result = PyObject_CallObject((PyObject *)item_type, args);
                Py_DECREF(args);
                Py_DECREF(hooked_values);
            }
        }

        Py_DECREF(item_id);
        return result;
    }

    Py_DECREF(item_id);
    Py_INCREF(item);
    return item;
}

static PyObject *fast_hook(PyObject *self, PyObject *args)
{
    PyObject *item;
    PyObject *magidict_class;

    if (!PyArg_ParseTuple(args, "OO", &item, &magidict_class))
    {
        return NULL;
    }

    PyObject *memo = PyDict_New();
    if (memo == NULL)
        return NULL;

    PyObject *result = fast_hook_with_memo(item, memo, magidict_class);
    Py_DECREF(memo);

    return result;
}

static PyObject *py_fast_hook_with_memo(PyObject *self, PyObject *args)
{
    PyObject *item;
    PyObject *memo;
    PyObject *magidict_class;

    if (!PyArg_ParseTuple(args, "OOO", &item, &memo, &magidict_class))
    {
        return NULL;
    }

    if (!PyDict_Check(memo))
    {
        PyErr_SetString(PyExc_TypeError, "memo must be a dictionary");
        return NULL;
    }

    return fast_hook_with_memo(item, memo, magidict_class);
}

static PyMethodDef module_methods[] = {
    {"fast_hook", fast_hook, METH_VARARGS,
     "Fast recursive conversion of dicts to MagiDicts (creates own memo)"},
    {"fast_hook_with_memo", py_fast_hook_with_memo, METH_VARARGS,
     "Fast recursive conversion of dicts to MagiDicts (uses provided memo)"},
    {NULL, NULL, 0, NULL}};

static PyModuleDef magidictmodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "magidict._magidict",
    .m_doc = "Fast C implementation of MagiDict hook function",
    .m_size = -1,
    .m_methods = module_methods,
};

PyMODINIT_FUNC PyInit__magidict(void)
{
    return PyModule_Create(&magidictmodule);
}