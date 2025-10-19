// magidict.c - Complete Safe C implementation of MagiDict using composition
// Fixed reference counting, memory management, and full method support

#include <Python.h>
#include <string.h>

// MagiDict structure - uses composition, not inheritance
typedef struct {
    PyObject_HEAD
    PyObject *dict;        // Internal dictionary
    int from_none;
    int from_missing;
} MagiDict;

static PyTypeObject MagiDictType;

// Forward declarations
static PyObject *MagiDict_HookWithMemo(PyObject *item, PyObject *memo);

// ============================================================================
// Initialization and Deallocation
// ============================================================================

static PyObject *MagiDict_new(PyTypeObject *type, PyObject *args, PyObject *kwargs) {
    MagiDict *self = (MagiDict *)type->tp_alloc(type, 0);
    if (self == NULL) return NULL;

    self->dict = PyDict_New();
    if (self->dict == NULL) {
        Py_DECREF(self);
        return NULL;
    }

    self->from_none = 0;
    self->from_missing = 0;
    return (PyObject *)self;
}

static int MagiDict_init(MagiDict *self, PyObject *args, PyObject *kwargs) {
    PyObject *arg = NULL;
    PyObject *memo = NULL;

    // Clear the dict first
    PyDict_Clear(self->dict);

    // Create memo dict for recursive hooking
    memo = PyDict_New();
    if (memo == NULL) return -1;

    // Handle initialization arguments
    if (PyTuple_Size(args) == 1 && (!kwargs || PyDict_Size(kwargs) == 0)) {
        arg = PyTuple_GetItem(args, 0);
        if (PyDict_Check(arg)) {
            PyObject *key;
            PyObject *value;
            Py_ssize_t pos = 0;

            while (PyDict_Next(arg, &pos, &key, &value)) {
                PyObject *hooked = MagiDict_HookWithMemo(value, memo);
                if (hooked == NULL) {
                    Py_DECREF(memo);
                    return -1;
                }

                int ret = PyDict_SetItem(self->dict, key, hooked);
                Py_DECREF(hooked);
                if (ret < 0) {
                    Py_DECREF(memo);
                    return -1;
                }
            }
        }
    } else if (kwargs) {
        PyObject *key;
        PyObject *value;
        Py_ssize_t pos = 0;

        while (PyDict_Next(kwargs, &pos, &key, &value)) {
            PyObject *hooked = MagiDict_HookWithMemo(value, memo);
            if (hooked == NULL) {
                Py_DECREF(memo);
                return -1;
            }

            int ret = PyDict_SetItem(self->dict, key, hooked);
            Py_DECREF(hooked);
            if (ret < 0) {
                Py_DECREF(memo);
                return -1;
            }
        }
    }

    Py_DECREF(memo);
    return 0;
}

static void MagiDict_dealloc(MagiDict *self) {
    if (self->dict != NULL) {
        Py_DECREF(self->dict);
    }
    Py_TYPE(self)->tp_free((PyObject *)self);
}

// ============================================================================
// Helper: Create empty MagiDict with flag
// ============================================================================

static PyObject *create_empty_magi_dict(int flag_type) {
    MagiDict *md = (MagiDict *)MagiDictType.tp_alloc(&MagiDictType, 0);
    if (md == NULL) return NULL;

    md->dict = PyDict_New();
    if (md->dict == NULL) {
        Py_DECREF(md);
        return NULL;
    }

    md->from_none = (flag_type == 1) ? 1 : 0;
    md->from_missing = (flag_type == 2) ? 1 : 0;

    return (PyObject *)md;
}

// ============================================================================
// Recursive Hooking
// ============================================================================

static PyObject *MagiDict_HookWithMemo(PyObject *item, PyObject *memo) {
    if (item == NULL) {
        return NULL;
    }

    PyObject *item_id = PyLong_FromVoidPtr((void *)item);
    if (item_id == NULL) {
        return NULL;
    }

    int has_key = PyDict_Contains(memo, item_id);
    if (has_key == -1) {
        Py_DECREF(item_id);
        return NULL;
    }

    if (has_key) {
        PyObject *cached = PyDict_GetItem(memo, item_id);
        Py_DECREF(item_id);
        Py_XINCREF(cached);
        return cached;
    }

    PyObject *result = NULL;

    if (PyObject_TypeCheck(item, &MagiDictType)) {
        Py_INCREF(item);
        result = item;
        PyDict_SetItem(memo, item_id, result);
    }
    else if (PyDict_Check(item)) {
        result = create_empty_magi_dict(0);
        if (result == NULL) {
            Py_DECREF(item_id);
            return NULL;
        }

        int memo_ret = PyDict_SetItem(memo, item_id, result);
        if (memo_ret < 0) {
            Py_DECREF(result);
            Py_DECREF(item_id);
            return NULL;
        }

        MagiDict *md = (MagiDict *)result;
        PyObject *k, *v;
        Py_ssize_t pos = 0;

        while (PyDict_Next(item, &pos, &k, &v)) {
            PyObject *hooked_v = MagiDict_HookWithMemo(v, memo);
            if (hooked_v == NULL) {
                Py_DECREF(result);
                Py_DECREF(item_id);
                return NULL;
            }
            int ret = PyDict_SetItem(md->dict, k, hooked_v);
            Py_DECREF(hooked_v);
            if (ret < 0) {
                Py_DECREF(result);
                Py_DECREF(item_id);
                return NULL;
            }
        }
    }
    else if (PyList_Check(item)) {
        PyDict_SetItem(memo, item_id, item);
        result = item;
        Py_INCREF(result);

        Py_ssize_t list_size = PyList_Size(item);
        for (Py_ssize_t i = 0; i < list_size; i++) {
            PyObject *elem = PyList_GetItem(item, i);
            if (elem == NULL) {
                Py_DECREF(result);
                Py_DECREF(item_id);
                return NULL;
            }
            PyObject *hooked_elem = MagiDict_HookWithMemo(elem, memo);
            if (hooked_elem == NULL) {
                Py_DECREF(result);
                Py_DECREF(item_id);
                return NULL;
            }
            int ret = PyList_SetItem(item, i, hooked_elem);
            if (ret < 0) {
                Py_DECREF(hooked_elem);
                Py_DECREF(result);
                Py_DECREF(item_id);
                return NULL;
            }
        }
    }
    else if (PyTuple_Check(item)) {
        Py_ssize_t size = PyTuple_Size(item);
        PyObject *hooked_tuple = PyTuple_New(size);
        if (hooked_tuple == NULL) {
            Py_DECREF(item_id);
            return NULL;
        }

        int memo_ret = PyDict_SetItem(memo, item_id, hooked_tuple);
        if (memo_ret < 0) {
            Py_DECREF(hooked_tuple);
            Py_DECREF(item_id);
            return NULL;
        }

        for (Py_ssize_t i = 0; i < size; i++) {
            PyObject *elem = PyTuple_GetItem(item, i);
            if (elem == NULL) {
                Py_DECREF(hooked_tuple);
                Py_DECREF(item_id);
                return NULL;
            }
            PyObject *hooked = MagiDict_HookWithMemo(elem, memo);
            if (hooked == NULL) {
                Py_DECREF(hooked_tuple);
                Py_DECREF(item_id);
                return NULL;
            }
            int ret = PyTuple_SetItem(hooked_tuple, i, hooked);
            if (ret < 0) {
                Py_DECREF(hooked_tuple);
                Py_DECREF(item_id);
                return NULL;
            }
        }
        result = hooked_tuple;
    }
    else {
        Py_INCREF(item);
        result = item;
    }

    Py_DECREF(item_id);
    return result;
}

// ============================================================================
// Dictionary Protocol Methods
// ============================================================================

static PyObject *MagiDict_subscript(MagiDict *self, PyObject *key) {
    if (PyUnicode_Check(key)) {
        const char *key_str = PyUnicode_AsUTF8(key);
        if (key_str && strchr(key_str, '.') != NULL) {
            PyObject *sep = PyUnicode_FromString(".");
            if (sep == NULL) return NULL;

            PyObject *keys = PyUnicode_Split(key, sep, -1);
            Py_DECREF(sep);

            if (keys == NULL) return NULL;

            PyObject *obj = (PyObject *)self;
            Py_INCREF(obj);

            for (Py_ssize_t i = 0; i < PyList_Size(keys); i++) {
                PyObject *k = PyList_GetItem(keys, i);

                if (PyObject_TypeCheck(obj, &MagiDictType)) {
                    MagiDict *md = (MagiDict *)obj;
                    PyObject *next = PyDict_GetItemWithError(md->dict, k);

                    if (next == NULL && PyErr_Occurred()) {
                        Py_DECREF(obj);
                        Py_DECREF(keys);
                        return NULL;
                    }

                    Py_DECREF(obj);
                    if (next == NULL) {
                        Py_DECREF(keys);
                        return create_empty_magi_dict(2);
                    }

                    obj = next;
                    Py_INCREF(obj);
                } else if (PyDict_Check(obj)) {
                    PyObject *next = PyDict_GetItemWithError(obj, k);

                    if (next == NULL && PyErr_Occurred()) {
                        Py_DECREF(obj);
                        Py_DECREF(keys);
                        return NULL;
                    }

                    Py_DECREF(obj);
                    if (next == NULL) {
                        Py_DECREF(keys);
                        return create_empty_magi_dict(2);
                    }

                    obj = next;
                    Py_INCREF(obj);
                } else {
                    Py_DECREF(obj);
                    Py_DECREF(keys);
                    return create_empty_magi_dict(2);
                }
            }

            if (obj == Py_None) {
                Py_DECREF(obj);
                Py_DECREF(keys);
                return create_empty_magi_dict(1);
            }

            Py_DECREF(keys);
            return obj;
        }
    }

    PyObject *value = PyDict_GetItemWithError(self->dict, key);
    if (value == NULL) {
        if (PyErr_Occurred()) return NULL;
        return create_empty_magi_dict(2);
    }

    Py_INCREF(value);
    return value;
}

static int MagiDict_ass_subscript(MagiDict *self, PyObject *key, PyObject *value) {
    if (self->from_none || self->from_missing) {
        PyErr_SetString(PyExc_TypeError, "Cannot modify NoneType or missing keys.");
        return -1;
    }

    if (value == NULL) {
        return PyDict_DelItem(self->dict, key);
    }

    PyObject *memo = PyDict_New();
    if (memo == NULL) return -1;

    PyObject *hooked = MagiDict_HookWithMemo(value, memo);
    Py_DECREF(memo);

    if (hooked == NULL) return -1;

    int ret = PyDict_SetItem(self->dict, key, hooked);
    Py_DECREF(hooked);
    return ret;
}

static Py_ssize_t MagiDict_length(MagiDict *self) {
    return PyDict_Size(self->dict);
}

static int MagiDict_contains(MagiDict *self, PyObject *key) {
    return PyDict_Contains(self->dict, key);
}

// ============================================================================
// Attribute Access
// ============================================================================

static PyObject *MagiDict_getattr(MagiDict *self, PyObject *name) {
    if (PyUnicode_Check(name)) {
        const char *name_str = PyUnicode_AsUTF8(name);
        if (name_str) {
            if (strcmp(name_str, "_from_none") == 0) {
                return PyBool_FromLong(self->from_none);
            }
            if (strcmp(name_str, "_from_missing") == 0) {
                return PyBool_FromLong(self->from_missing);
            }
        }
    }

    PyObject *value = PyDict_GetItemWithError(self->dict, name);
    if (value != NULL) {
        if (value == Py_None) {
            return create_empty_magi_dict(1);
        }
        Py_INCREF(value);
        return value;
    }

    if (PyErr_Occurred()) {
        PyErr_Clear();
    }

    return create_empty_magi_dict(2);
}

static int MagiDict_setattr(MagiDict *self, PyObject *name, PyObject *value) {
    PyErr_SetString(PyExc_AttributeError, "Cannot modify MagiDict attributes");
    return -1;
}

// ============================================================================
// Boolean Evaluation
// ============================================================================

static int MagiDict_bool(MagiDict *self) {
    // Empty MagiDicts from None/missing are falsy
    if (self->from_none || self->from_missing) {
        return 0;
    }
    return PyDict_Size(self->dict) > 0 ? 1 : 0;
}

// ============================================================================
// Methods
// ============================================================================

static PyObject *MagiDict_mget(MagiDict *self, PyObject *args) {
    PyObject *key = NULL;
    PyObject *default_val = NULL;

    if (!PyArg_ParseTuple(args, "O|O", &key, &default_val)) {
        return NULL;
    }

    PyObject *value = PyDict_GetItemWithError(self->dict, key);

    if (value == NULL && PyErr_Occurred()) {
        return NULL;
    }

    if (value == NULL) {
        if (default_val == NULL) {
            return create_empty_magi_dict(2);
        }
        Py_INCREF(default_val);
        return default_val;
    }

    if (value == Py_None) {
        return create_empty_magi_dict(1);
    }

    Py_INCREF(value);
    return value;
}

static PyObject *MagiDict_disenchant(MagiDict *self, PyObject *args) {
    PyObject *result = PyDict_New();
    if (result == NULL) return NULL;

    PyObject *key, *value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(self->dict, &pos, &key, &value)) {
        PyObject *converted;
        if (PyObject_TypeCheck(value, &MagiDictType)) {
            MagiDict *nested = (MagiDict *)value;
            converted = PyObject_CallMethod((PyObject *)nested, "disenchant", NULL);
            if (converted == NULL) {
                Py_DECREF(result);
                return NULL;
            }
        } else if (PyDict_Check(value)) {
            converted = PyDict_New();
            if (converted == NULL) {
                Py_DECREF(result);
                return NULL;
            }
            if (PyDict_Update(converted, value) < 0) {
                Py_DECREF(converted);
                Py_DECREF(result);
                return NULL;
            }
        } else if (PyList_Check(value)) {
            Py_ssize_t list_size = PyList_Size(value);
            converted = PyList_New(list_size);
            if (converted == NULL) {
                Py_DECREF(result);
                return NULL;
            }
            for (Py_ssize_t i = 0; i < list_size; i++) {
                PyObject *elem = PyList_GetItem(value, i);
                PyObject *elem_converted;
                
                if (PyObject_TypeCheck(elem, &MagiDictType)) {
                    MagiDict *nested = (MagiDict *)elem;
                    elem_converted = PyObject_CallMethod((PyObject *)nested, "disenchant", NULL);
                } else if (PyDict_Check(elem)) {
                    elem_converted = PyDict_New();
                    if (elem_converted && PyDict_Update(elem_converted, elem) < 0) {
                        Py_DECREF(elem_converted);
                        elem_converted = NULL;
                    }
                } else {
                    elem_converted = elem;
                    Py_INCREF(elem_converted);
                }
                
                if (elem_converted == NULL) {
                    Py_DECREF(converted);
                    Py_DECREF(result);
                    return NULL;
                }
                PyList_SetItem(converted, i, elem_converted);
            }
        } else if (PyTuple_Check(value)) {
            Py_ssize_t tuple_size = PyTuple_Size(value);
            converted = PyTuple_New(tuple_size);
            if (converted == NULL) {
                Py_DECREF(result);
                return NULL;
            }
            for (Py_ssize_t i = 0; i < tuple_size; i++) {
                PyObject *elem = PyTuple_GetItem(value, i);
                PyObject *elem_converted;
                
                if (PyObject_TypeCheck(elem, &MagiDictType)) {
                    MagiDict *nested = (MagiDict *)elem;
                    elem_converted = PyObject_CallMethod((PyObject *)nested, "disenchant", NULL);
                } else if (PyDict_Check(elem)) {
                    elem_converted = PyDict_New();
                    if (elem_converted && PyDict_Update(elem_converted, elem) < 0) {
                        Py_DECREF(elem_converted);
                        elem_converted = NULL;
                    }
                } else {
                    elem_converted = elem;
                    Py_INCREF(elem_converted);
                }
                
                if (elem_converted == NULL) {
                    Py_DECREF(converted);
                    Py_DECREF(result);
                    return NULL;
                }
                PyTuple_SetItem(converted, i, elem_converted);
            }
        } else {
            converted = value;
            Py_INCREF(converted);
        }

        int ret = PyDict_SetItem(result, key, converted);
        Py_DECREF(converted);
        if (ret < 0) {
            Py_DECREF(result);
            return NULL;
        }
    }

    return result;
}

static PyObject *MagiDict_repr(MagiDict *self) {
    PyObject *dict_repr = PyObject_Repr(self->dict);
    if (dict_repr == NULL) return NULL;

    PyObject *result = PyUnicode_FromFormat("MagiDict(%U)", dict_repr);
    Py_DECREF(dict_repr);
    return result;
}

static PyObject *MagiDict_dir(MagiDict *self) {
    PyObject *keys = PyDict_Keys(self->dict);
    if (keys == NULL) return NULL;

    PyObject *result = PyList_New(0);
    if (result == NULL) {
        Py_DECREF(keys);
        return NULL;
    }

    Py_ssize_t size = PyList_Size(keys);
    for (Py_ssize_t i = 0; i < size; i++) {
        PyObject *key = PyList_GetItem(keys, i);
        if (PyUnicode_Check(key)) {
            if (PyList_Append(result, key) < 0) {
                Py_DECREF(result);
                Py_DECREF(keys);
                return NULL;
            }
        }
    }

    Py_DECREF(keys);
    return result;
}

static PyObject *MagiDict_getstate(MagiDict *self) {
    PyObject *state = PyDict_New();
    if (state == NULL) return NULL;

    PyObject *data_dict = PyDict_New();
    if (data_dict == NULL) {
        Py_DECREF(state);
        return NULL;
    }

    if (PyDict_Update(data_dict, self->dict) < 0) {
        Py_DECREF(data_dict);
        Py_DECREF(state);
        return NULL;
    }

    if (PyDict_SetItemString(state, "data", data_dict) < 0) {
        Py_DECREF(data_dict);
        Py_DECREF(state);
        return NULL;
    }
    Py_DECREF(data_dict);

    PyObject *from_none = PyBool_FromLong(self->from_none);
    if (PyDict_SetItemString(state, "_from_none", from_none) < 0) {
        Py_DECREF(from_none);
        Py_DECREF(state);
        return NULL;
    }
    Py_DECREF(from_none);

    PyObject *from_missing = PyBool_FromLong(self->from_missing);
    if (PyDict_SetItemString(state, "_from_missing", from_missing) < 0) {
        Py_DECREF(from_missing);
        Py_DECREF(state);
        return NULL;
    }
    Py_DECREF(from_missing);

    return state;
}

static PyObject *MagiDict_setstate(MagiDict *self, PyObject *state) {
    if (!PyDict_Check(state)) {
        PyErr_SetString(PyExc_TypeError, "state must be a dict");
        return NULL;
    }

    PyObject *from_none_obj = PyDict_GetItemString(state, "_from_none");
    if (from_none_obj != NULL) {
        self->from_none = PyObject_IsTrue(from_none_obj);
    }

    PyObject *from_missing_obj = PyDict_GetItemString(state, "_from_missing");
    if (from_missing_obj != NULL) {
        self->from_missing = PyObject_IsTrue(from_missing_obj);
    }

    PyObject *data = PyDict_GetItemString(state, "data");
    if (data != NULL && PyDict_Check(data)) {
        PyDict_Clear(self->dict);
        if (PyDict_Update(self->dict, data) < 0) {
            return NULL;
        }
    }

    Py_RETURN_NONE;
}

static PyObject *MagiDict_reduce_ex(MagiDict *self, PyObject *args) {
    return PyObject_CallMethod((PyObject *)self, "__reduce_ex__", "i", 2);
}

// ============================================================================
// Method Definitions
// ============================================================================

static PyMethodDef MagiDict_methods[] = {
    {"mget", (PyCFunction)MagiDict_mget, METH_VARARGS,
     "Safe get method that returns empty MagiDict for missing keys"},
    {"mg", (PyCFunction)MagiDict_mget, METH_VARARGS,
     "Shorthand for mget"},
    {"disenchant", (PyCFunction)MagiDict_disenchant, METH_NOARGS,
     "Convert MagiDict and nested MagiDicts back to standard dicts"},
    {"__dir__", (PyCFunction)MagiDict_dir, METH_NOARGS,
     "Return list of valid attributes"},
    {"__getstate__", (PyCFunction)MagiDict_getstate, METH_NOARGS,
     "Get state for pickling"},
    {"__setstate__", (PyCFunction)MagiDict_setstate, METH_O,
     "Set state from pickling"},
    {NULL, NULL, 0, NULL}
};

static PyMappingMethods MagiDict_as_mapping = {
    .mp_length = (lenfunc)MagiDict_length,
    .mp_subscript = (binaryfunc)MagiDict_subscript,
    .mp_ass_subscript = (objobjargproc)MagiDict_ass_subscript,
};

static PySequenceMethods MagiDict_as_sequence = {
    .sq_contains = (objobjproc)MagiDict_contains,
};

// ============================================================================
// Type Definition
// ============================================================================

static PyTypeObject MagiDictType = {
    PyVarObject_HEAD_INIT(NULL, 0)
        .tp_name = "magidict._magidict.MagiDict",
    .tp_doc = "A forgiving dictionary with attribute-style access and safe nested access",
    .tp_basicsize = sizeof(MagiDict),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = (newfunc)MagiDict_new,
    .tp_init = (initproc)MagiDict_init,
    .tp_dealloc = (destructor)MagiDict_dealloc,
    .tp_repr = (reprfunc)MagiDict_repr,
    .tp_getattro = (getattrofunc)MagiDict_getattr,
    .tp_setattro = (setattrofunc)MagiDict_setattr,
    .tp_as_mapping = &MagiDict_as_mapping,
    .tp_as_sequence = &MagiDict_as_sequence,
    .tp_methods = MagiDict_methods,
    .nb_bool = (inquiry)MagiDict_bool,
};

// ============================================================================
// Module Initialization
// ============================================================================

static PyModuleDef magidictmodule = {
    PyModuleDef_HEAD_INIT,
    "magidict._magidict",
    "MagiDict - A forgiving dictionary implementation in C",
    -1,
    NULL, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC PyInit__magidict(void) {
    PyObject *m;

    // Update NumberMethods structure
    PyType_Slot slots[] = {
        {Py_nb_bool, (inquiry)MagiDict_bool},
        {0, NULL}
    };

    if (PyType_Ready(&MagiDictType) < 0)
        return NULL;

    m = PyModule_Create(&magidictmodule);
    if (m == NULL)
        return NULL;

    Py_INCREF(&MagiDictType);
    if (PyModule_AddObject(m, "MagiDict", (PyObject *)&MagiDictType) < 0) {
        Py_DECREF(&MagiDictType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}