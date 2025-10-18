// magidict.c - C implementation of MagiDict with CFFI bindings

#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// MagiDict structure
typedef struct {
    PyDictObject dict;
    int from_none;
    int from_missing;
} MagiDict;

static PyTypeObject MagiDictType;

// Forward declarations
static PyObject* MagiDict_Hook(PyObject* item);
static PyObject* MagiDict_HookWithMemo(PyObject* item, PyObject* memo);

// Helper: Create empty MagiDict with flag
static PyObject* create_empty_magi_dict(int flag_type) {
    MagiDict* md = (MagiDict*)PyDict_New();
    if (flag_type == 1) {
        md->from_none = 1;
    } else if (flag_type == 2) {
        md->from_missing = 1;
    }
    return (PyObject*)md;
}

// New method
static PyObject* MagiDict_new(PyTypeObject* type, PyObject* args, PyObject* kwargs) {
    MagiDict* self = (MagiDict*)PyDict_New();
    if (self == NULL) return NULL;
    self->from_none = 0;
    self->from_missing = 0;
    return (PyObject*)self;
}

// Init method
static int MagiDict_init(PyObject* self, PyObject* args, PyObject* kwargs) {
    MagiDict* md = (MagiDict*)self;
    PyObject* input_dict = NULL;
    PyObject* memo = PyDict_New();
    if (memo == NULL) return -1;

    if (PyDict_Size((PyObject*)md) > 0) {
        Py_DECREF(memo);
        return 0;
    }

    if (PyTuple_Size(args) == 1 && (!kwargs || PyDict_Size(kwargs) == 0)) {
        PyObject* arg = PyTuple_GetItem(args, 0);
        if (PyDict_Check(arg)) {
            input_dict = arg;
        } else {
            input_dict = PyDict_New();
            int ret = PyDict_Update(input_dict, arg);
            if (ret < 0) {
                Py_DECREF(memo);
                Py_DECREF(input_dict);
                return -1;
            }
        }
    } else {
        input_dict = PyDict_New();
        int ret = PyDict_Update(input_dict, PyDict_New());
        if (kwargs) PyDict_Update(input_dict, kwargs);
    }

    PyObject *key, *value;
    Py_ssize_t pos = 0;
    while (PyDict_Next(input_dict, &pos, &key, &value)) {
        PyObject* hooked = MagiDict_HookWithMemo(value, memo);
        PyDict_SetItem((PyObject*)md, key, hooked);
        Py_DECREF(hooked);
    }

    Py_DECREF(memo);
    return 0;
}

// Recursive hooking function
static PyObject* MagiDict_HookWithMemo(PyObject* item, PyObject* memo) {
    if (item == NULL) return NULL;

    // Check if already in memo
    PyObject* item_id = PyLong_FromVoidPtr((void*)item);
    if (PyDict_Contains(memo, item_id)) {
        PyObject* cached = PyDict_GetItem(memo, item_id);
        Py_DECREF(item_id);
        Py_XINCREF(cached);
        return cached;
    }

    PyObject* result = NULL;

    if (PyDict_Check(item)) {
        result = MagiDict_new(&MagiDictType, PyTuple_New(0), NULL);
        PyDict_SetItem(memo, item_id, result);

        PyObject *k, *v;
        Py_ssize_t pos = 0;
        while (PyDict_Next(item, &pos, &k, &v)) {
            PyObject* hooked_v = MagiDict_HookWithMemo(v, memo);
            PyDict_SetItem(result, k, hooked_v);
            Py_DECREF(hooked_v);
        }
    } else if (PyList_Check(item)) {
        PyDict_SetItem(memo, item_id, item);
        result = item;
        Py_INCREF(result);

        for (Py_ssize_t i = 0; i < PyList_Size(item); i++) {
            PyObject* elem = PyList_GetItem(item, i);
            PyObject* hooked_elem = MagiDict_HookWithMemo(elem, memo);
            PyList_SetItem(item, i, hooked_elem);
        }
    } else if (PyTuple_Check(item)) {
        PyObject* hooked_tuple = PyTuple_New(PyTuple_Size(item));
        for (Py_ssize_t i = 0; i < PyTuple_Size(item); i++) {
            PyObject* elem = PyTuple_GetItem(item, i);
            PyObject* hooked = MagiDict_HookWithMemo(elem, memo);
            PyTuple_SetItem(hooked_tuple, i, hooked);
        }
        result = hooked_tuple;
    } else {
        Py_INCREF(item);
        result = item;
    }

    Py_DECREF(item_id);
    return result;
}

static PyObject* MagiDict_Hook(PyObject* item) {
    PyObject* memo = PyDict_New();
    PyObject* result = MagiDict_HookWithMemo(item, memo);
    Py_DECREF(memo);
    return result;
}

// __getitem__ method
static PyObject* MagiDict_getitem(PyObject* self, PyObject* key) {
    MagiDict* md = (MagiDict*)self;

    // Handle string keys with dots
    if (PyUnicode_Check(key)) {
        const char* key_str = PyUnicode_AsUTF8(key);
        if (strchr(key_str, '.') != NULL) {
            PyObject* keys = PyUnicode_Split(key, PyUnicode_FromString("."), -1);
            PyObject* obj = self;
            for (Py_ssize_t i = 0; i < PyList_Size(keys); i++) {
                PyObject* k = PyList_GetItem(keys, i);
                if (PyDict_Check(obj)) {
                    if (PyDict_Contains(obj, k)) {
                        obj = PyDict_GetItem(obj, k);
                    } else {
                        Py_DECREF(keys);
                        return create_empty_magi_dict(2);
                    }
                }
            }
            if (obj == Py_None) {
                Py_DECREF(keys);
                return create_empty_magi_dict(1);
            }
            Py_DECREF(keys);
            Py_INCREF(obj);
            return obj;
        }
    }

    // Standard dict access
    return PyDict_GetItem((PyObject*)md, key);
}

// __getattr__ method
static PyObject* MagiDict_getattr(PyObject* self, PyObject* name) {
    MagiDict* md = (MagiDict*)self;

    if (PyDict_Contains((PyObject*)md, name)) {
        PyObject* value = PyDict_GetItem((PyObject*)md, name);
        if (value == Py_None) {
            return create_empty_magi_dict(1);
        }
        Py_INCREF(value);
        return value;
    }

    return create_empty_magi_dict(2);
}

// mget method
static PyObject* MagiDict_mget(PyObject* self, PyObject* args) {
    PyObject* key = NULL;
    PyObject* default_val = NULL;

    if (!PyArg_ParseTuple(args, "O|O", &key, &default_val)) {
        return NULL;
    }

    MagiDict* md = (MagiDict*)self;
    if (!default_val) {
        default_val = create_empty_magi_dict(2);
    }

    if (PyDict_Contains((PyObject*)md, key)) {
        PyObject* value = PyDict_GetItem((PyObject*)md, key);
        if (value == Py_None) {
            return create_empty_magi_dict(1);
        }
        Py_INCREF(value);
        return value;
    }

    Py_INCREF(default_val);
    return default_val;
}

// disenchant method - convert to regular dict
static PyObject* MagiDict_disenchant(PyObject* self, PyObject* args) {
    PyObject* memo = PyDict_New();
    PyObject* result = NULL;

    // Recursively convert MagiDict to dict
    if (PyDict_Check(self)) {
        result = PyDict_New();
        PyObject *key, *value;
        Py_ssize_t pos = 0;
        while (PyDict_Next(self, &pos, &key, &value)) {
            PyDict_SetItem(result, key, value);
        }
    }

    Py_DECREF(memo);
    return result ? result : PyDict_New();
}

// Method definitions
static PyMethodDef MagiDict_methods[] = {
    {"mget", MagiDict_mget, METH_VARARGS, "Safe get method"},
    {"mg", MagiDict_mget, METH_VARARGS, "Shorthand for mget"},
    {"disenchant", MagiDict_disenchant, METH_NOARGS, "Convert to regular dict"},
    {NULL}
};

// Type definition
static PyTypeObject MagiDictType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "magidict.MagiDict",
    .tp_doc = "A forgiving dictionary with attribute access",
    .tp_basicsize = sizeof(MagiDict),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = MagiDict_new,
    .tp_init = MagiDict_init,
    .tp_methods = MagiDict_methods,
    .tp_base = &PyDict_Type,
};

// Module initialization
static PyModuleDef magidictmodule = {
    PyModuleDef_HEAD_INIT,
    "magidict",
    "MagiDict - A forgiving dictionary implementation",
    -1,
    NULL, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC PyInit_magidict(void) {
    PyObject* m;

    if (PyType_Ready(&MagiDictType) < 0)
        return NULL;

    m = PyModule_Create(&magidictmodule);
    if (m == NULL)
        return NULL;

    Py_INCREF(&MagiDictType);
    if (PyModule_AddObject(m, "MagiDict", (PyObject*)&MagiDictType) < 0) {
        Py_DECREF(&MagiDictType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}