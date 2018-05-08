import functools
from io import StringIO
import math
import operator
import tempfile

import numpy
import pytest

import xchainer
import xchainer.testing


_shapes = [
    (),
    (0,),
    (1,),
    (2, 3),
    (1, 1, 1),
    (2, 0, 3),
]


@pytest.fixture(params=_shapes)
def shape(request):
    return request.param


def _total_size(shape):
    return functools.reduce(operator.mul, shape, 1)


def _check_device(a, device=None):
    if device is None:
        device = xchainer.get_default_device()
    elif isinstance(device, str):
        device = xchainer.get_device(device)
    assert a.device is device


def _create_dummy_ndarray(xp, shape, dtype, device=None):
    if xchainer.dtype(dtype).name in xchainer.testing.unsigned_dtypes:
        start = 0
        stop = _total_size(shape)
    else:
        start = -1
        stop = _total_size(shape) - 1

    if xp is xchainer:
        return xp.arange(start=start, stop=stop, device=device).reshape(shape).astype(dtype)
    else:
        return xp.arange(start=start, stop=stop).reshape(shape).astype(dtype)


_array_params_nonfloat_list = [
    -2,
    1,
    -1.5,
    2.3,
    True,
    False,
    numpy.array(1),
]


_array_params_float_list = [
    float('inf'),
    float('nan'),
]


_array_params_list = _array_params_nonfloat_list + _array_params_float_list


def _array_params(list):
    return list + [
        list,
        [list, list],
        (list, list),
        tuple(list),
        (tuple(list), tuple(list)),
        [tuple(list), tuple(list)],
    ]


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('obj', _array_params(_array_params_list))
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_array_from_python_tuple_or_list(xp, obj, device):
    return xp.array(obj)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@pytest.mark.parametrize('obj', _array_params(_array_params_nonfloat_list))
@xchainer.testing.parametrize_dtype_specifier('dtype_spec', dtypes=xchainer.testing.nonfloat_dtypes, additional_args=(None,))
def test_array_from_python_tuple_or_list_with_nonfloat_dtype(xp, obj, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    return xp.array(obj, dtype_spec)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@pytest.mark.parametrize('obj', _array_params(_array_params_list))
@xchainer.testing.parametrize_dtype_specifier('dtype_spec', dtypes=xchainer.testing.float_dtypes, additional_args=(None,))
def test_array_from_python_tuple_or_list_with_float_dtype(xp, obj, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    return xp.array(obj, dtype_spec)


@pytest.mark.parametrize('obj', _array_params(_array_params_list))
@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_array_from_python_tuple_or_list_with_device(obj, device):
    a = xchainer.array(obj, 'float32', device=device)
    b = xchainer.array(obj, 'float32')
    xchainer.testing.assert_array_equal(a, b)
    _check_device(a, device)


def _check_array_from_numpy_array(a_xc, a_np, device=None):
    assert a_xc.is_contiguous
    assert a_xc.offset == 0
    _check_device(a_xc, device)

    # recovered data should be equal
    a_np_recovered = xchainer.tonumpy(a_xc)
    xchainer.testing.assert_array_equal(a_xc, a_np_recovered)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_array_from_numpy_array(xp, shape, dtype, device):
    a_np = _create_dummy_ndarray(numpy, shape, dtype)
    a_xp = xp.array(a_np)

    if xp is xchainer:
        _check_array_from_numpy_array(a_xp, a_np, device)

        # test possibly freed memory
        a_np_copy = a_np.copy()
        del a_np
        xchainer.testing.assert_array_equal(a_xp, a_np_copy)

    return a_xp


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_array_from_numpy_non_contiguous_array(xp, shape, dtype, device):
    a_np = _create_dummy_ndarray(numpy, shape, dtype).T
    a_xp = xp.array(a_np)

    if xp is xchainer:
        _check_array_from_numpy_array(a_xp, a_np, device)

        # test possibly freed memory
        a_np_copy = a_np.copy()
        del a_np
        xchainer.testing.assert_array_equal(a_xp, a_np_copy)

    return a_xp


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_array_from_numpy_positive_offset_array(xp, device):
    a_np = _create_dummy_ndarray(numpy, (2, 3), 'int32')[1, 1:]
    a_xp = xp.array(a_np)

    if xp is xchainer:
        _check_array_from_numpy_array(a_xp, a_np, device)

        # test possibly freed memory
        a_np_copy = a_np.copy()
        del a_np
        xchainer.testing.assert_array_equal(a_xp, a_np_copy)

    return a_xp


def _array_from_numpy_array_with_dtype(xp, shape, src_dtype, dst_dtype_spec):
    if xp is numpy and isinstance(dst_dtype_spec, xchainer.dtype):
        dst_dtype_spec = dst_dtype_spec.name
    t = _create_dummy_ndarray(numpy, shape, src_dtype)
    return xp.array(t, dtype=dst_dtype_spec)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@pytest.mark.parametrize('src_dtype', xchainer.testing.all_dtypes)
@pytest.mark.parametrize('dst_dtype', xchainer.testing.all_dtypes)
def test_array_from_numpy_array_with_dtype(xp, shape, src_dtype, dst_dtype, device):
    return _array_from_numpy_array_with_dtype(xp, shape, src_dtype, dst_dtype)


@xchainer.testing.numpy_xchainer_array_equal()
@xchainer.testing.parametrize_dtype_specifier('dst_dtype_spec', additional_args=(None,))
def test_array_from_numpy_array_with_dtype_spec(xp, shape, dst_dtype_spec):
    return _array_from_numpy_array_with_dtype(xp, shape, 'float32', dst_dtype_spec)


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_array_from_numpy_array_with_device(shape, device):
    orig = _create_dummy_ndarray(numpy, (2, ), 'float32')
    a = xchainer.array(orig, device=device)
    b = xchainer.array(orig)
    xchainer.testing.assert_array_equal(a, b)
    _check_device(a, device)


@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@pytest.mark.parametrize('copy', [True, False])
def test_array_from_xchainer_array(shape, dtype, copy, device):
    t = _create_dummy_ndarray(xchainer, shape, dtype, device=device)
    a = xchainer.array(t, copy=copy)
    if not copy:
        assert t is a
    else:
        assert t is not a
        xchainer.testing.assert_array_equal(a, t)
        assert a.dtype == t.dtype
        assert a.device is t.device


def _check_array_from_xchainer_array_with_dtype(shape, src_dtype, dst_dtype_spec, copy, device=None):
    t = _create_dummy_ndarray(xchainer, shape, src_dtype, device=device)
    a = xchainer.array(t, dtype=dst_dtype_spec, copy=copy)

    src_dtype = xchainer.dtype(src_dtype)
    dst_dtype = src_dtype if dst_dtype_spec is None else xchainer.dtype(dst_dtype_spec)
    device = xchainer.get_device(device)

    if not copy and src_dtype == dst_dtype and device is xchainer.get_default_device():
        assert t is a
    else:
        assert t is not a
        xchainer.testing.assert_array_equal(a, t.astype(dst_dtype))
        assert a.dtype == dst_dtype
        assert a.device is xchainer.get_default_device()


@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@pytest.mark.parametrize('src_dtype', xchainer.testing.all_dtypes)
@pytest.mark.parametrize('dst_dtype', xchainer.testing.all_dtypes)
@pytest.mark.parametrize('copy', [True, False])
def test_array_from_xchainer_array_with_dtype(shape, src_dtype, dst_dtype, copy, device):
    _check_array_from_xchainer_array_with_dtype(shape, src_dtype, dst_dtype, copy, device)


@xchainer.testing.parametrize_dtype_specifier('dst_dtype_spec', additional_args=(None,))
@pytest.mark.parametrize('copy', [True, False])
def test_array_from_xchainer_array_with_dtype_spec(shape, dst_dtype_spec, copy):
    _check_array_from_xchainer_array_with_dtype(shape, 'float32', dst_dtype_spec, copy)


@pytest.mark.parametrize('src_dtype', xchainer.testing.all_dtypes)
@pytest.mark.parametrize('dst_dtype', xchainer.testing.all_dtypes)
@pytest.mark.parametrize('copy', [True, False])
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@pytest.mark.parametrize('dst_device_spec', [None, 'native:1', xchainer.get_device('native:1'), 'native:0'])
def test_array_from_xchainer_array_with_device(src_dtype, dst_dtype, copy, device, dst_device_spec):
    t = _create_dummy_ndarray(xchainer, (2,), src_dtype, device=device)
    a = xchainer.array(t, dtype=dst_dtype, copy=copy, device=dst_device_spec)

    dst_device = xchainer.get_device(dst_device_spec)

    if not copy and src_dtype == dst_dtype and device is dst_device:
        assert t is a
    else:
        assert t is not a
        xchainer.testing.assert_array_equal(a, t.to_device(dst_device).astype(dst_dtype))
        assert a.dtype == xchainer.dtype(dst_dtype)
        assert a.device is dst_device


def test_asarray_from_python_tuple_or_list():
    obj = _array_params_list
    a = xchainer.asarray(obj, dtype='float32')
    e = xchainer.array(obj, dtype='float32', copy=False)
    xchainer.testing.assert_array_equal(e, a)
    assert e.dtype == a.dtype
    assert e.device is a.device


def test_asarray_from_numpy_array():
    obj = _create_dummy_ndarray(numpy, (2, 3), 'int32')
    a = xchainer.asarray(obj, dtype='float32')
    e = xchainer.array(obj, dtype='float32', copy=False)
    xchainer.testing.assert_array_equal(e, a)
    assert e.dtype == a.dtype
    assert e.device is a.device


@pytest.mark.parametrize('dtype', ['int32', 'float32'])
def test_asarray_from_xchainer_array(dtype):
    obj = _create_dummy_ndarray(xchainer, (2, 3), 'int32')
    a = xchainer.asarray(obj, dtype=dtype)
    if a.dtype == obj.dtype:
        assert a is obj
    else:
        assert a is not obj
    e = xchainer.array(obj, dtype=dtype, copy=False)
    xchainer.testing.assert_array_equal(e, a)
    assert e.dtype == a.dtype
    assert e.device is a.device


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_asarray_with_device(device):
    a = xchainer.asarray([0, 1], 'float32', device)
    b = xchainer.asarray([0, 1], 'float32')
    xchainer.testing.assert_array_equal(a, b)
    _check_device(a, device)


def test_asanyarray_from_python_tuple_or_list():
    obj = _array_params_list
    a = xchainer.asanyarray(obj, dtype='float32')
    e = xchainer.array(obj, dtype='float32', copy=False)
    xchainer.testing.assert_array_equal(e, a)
    assert e.dtype == a.dtype
    assert e.device is a.device


def test_asanyarray_from_numpy_array():
    obj = _create_dummy_ndarray(numpy, (2, 3), 'int32')
    a = xchainer.asanyarray(obj, dtype='float32')
    e = xchainer.array(obj, dtype='float32', copy=False)
    xchainer.testing.assert_array_equal(e, a)
    assert e.dtype == a.dtype
    assert e.device is a.device


def test_asanyarray_from_numpy_subclass_array():
    class Subclass(numpy.ndarray):
        pass
    obj = _create_dummy_ndarray(numpy, (2, 3), 'int32').view(Subclass)
    a = xchainer.asanyarray(obj, dtype='float32')
    e = xchainer.array(obj, dtype='float32', copy=False)
    xchainer.testing.assert_array_equal(e, a)
    assert e.dtype == a.dtype
    assert e.device is a.device


@pytest.mark.parametrize('dtype', ['int32', 'float32'])
def test_asanyarray_from_xchainer_array(dtype):
    obj = _create_dummy_ndarray(xchainer, (2, 3), 'int32')
    a = xchainer.asanyarray(obj, dtype=dtype)
    if a.dtype == obj.dtype:
        assert a is obj
    else:
        assert a is not obj
    e = xchainer.array(obj, dtype=dtype, copy=False)
    xchainer.testing.assert_array_equal(e, a)
    assert e.dtype == a.dtype
    assert e.device is a.device


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_asanyarray_with_device(device):
    a = xchainer.asanyarray([0, 1], 'float32', device)
    b = xchainer.asanyarray([0, 1], 'float32')
    xchainer.testing.assert_array_equal(a, b)
    _check_device(a, device)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_empty(xp, shape, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    a = xp.empty(shape, dtype_spec)
    a.fill(0)
    return a


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_empty_with_device(device):
    a = xchainer.empty((2,), 'float32', device)
    b = xchainer.empty((2,), 'float32')
    _check_device(a, device)
    assert a.dtype == b.dtype
    assert a.shape == b.shape


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_empty_like(xp, shape, dtype, device):
    t = xp.empty(shape, dtype)
    a = xp.empty_like(t)
    a.fill(0)
    return a


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_empty_like_with_device(device):
    t = xchainer.empty((2,), 'float32')
    a = xchainer.empty_like(t, device)
    b = xchainer.empty_like(t)
    _check_device(a, device)
    assert a.dtype == b.dtype
    assert a.shape == b.shape


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_zeros(xp, shape, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    return xp.zeros(shape, dtype_spec)


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_zeros_with_device(device):
    a = xchainer.zeros((2,), 'float32', device)
    b = xchainer.zeros((2,), 'float32')
    xchainer.testing.assert_array_equal(a, b)
    _check_device(a, device)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_zeros_like(xp, shape, dtype, device):
    t = xp.empty(shape, dtype)
    return xp.zeros_like(t)


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_zeros_like_with_device(device):
    t = xchainer.empty((2,), 'float32')
    a = xchainer.zeros_like(t, device)
    b = xchainer.zeros_like(t)
    _check_device(a, device)
    xchainer.testing.assert_array_equal(a, b)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_ones(xp, shape, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    return xp.ones(shape, dtype_spec)


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_ones_with_device(device):
    a = xchainer.ones((2,), 'float32', device)
    b = xchainer.ones((2,), 'float32')
    _check_device(a, device)
    xchainer.testing.assert_array_equal(a, b)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_ones_like(xp, shape, dtype, device):
    t = xp.empty(shape, dtype)
    return xp.ones_like(t)


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_ones_like_with_device(shape, device):
    t = xchainer.empty((2,), 'float32')
    a = xchainer.ones_like(t, device)
    b = xchainer.ones_like(t)
    _check_device(a, device)
    xchainer.testing.assert_array_equal(a, b)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('value', [True, False, -2, 0, 1, 2, 2.3, float('inf'), float('nan')])
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_full(xp, shape, value, device):
    return xp.full(shape, value)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('value', [True, False, -2, 0, 1, 2, 2.3, float('inf'), float('nan')])
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_full_with_dtype(xp, shape, dtype_spec, value, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    return xp.full(shape, value, dtype_spec)


@pytest.mark.parametrize('value', [True, False, -2, 0, 1, 2, 2.3, float('inf'), float('nan')])
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_full_with_scalar(shape, dtype, value, device):
    scalar = xchainer.Scalar(value, dtype)
    a = xchainer.full(shape, scalar)
    if scalar.dtype in (xchainer.float32, xchainer.float64) and math.isnan(float(scalar)):
        assert all([math.isnan(el) for el in a._debug_flat_data])
    else:
        assert a._debug_flat_data == [scalar.tolist()] * a.total_size


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_full_with_device(device):
    a = xchainer.full((2,), 1, 'float32', device)
    b = xchainer.full((2,), 1, 'float32')
    _check_device(a, device)
    xchainer.testing.assert_array_equal(a, b)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('value', [True, False, -2, 0, 1, 2, 2.3, float('inf'), float('nan')])
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_full_like(xp, shape, dtype, value, device):
    t = xp.empty(shape, dtype)
    return xp.full_like(t, value)


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_full_like_with_device(device):
    t = xchainer.empty((2,), 'float32')
    a = xchainer.full_like(t, 1, device)
    b = xchainer.full_like(t, 1)
    _check_device(a, device)
    xchainer.testing.assert_array_equal(a, b)


def _is_bool_spec(dtype_spec):
    # Used in arange tests
    if dtype_spec is None:
        return False
    return xchainer.dtype(dtype_spec) == xchainer.bool_


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('stop', [-2, 0, 0.1, 3, 3.2, False, True])
@pytest.mark.parametrize_device(['native:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec', additional_args=(None,))
def test_arange_stop(xp, stop, dtype_spec, device):
    # TODO(hvy): xp.arange(True) should return an ndarray of type int64
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    if _is_bool_spec(dtype_spec) and stop > 2:  # Checked in test_invalid_arange_too_long_bool
        return xchainer.testing.ignore()
    if isinstance(stop, bool) and dtype_spec is None:
        # TODO(niboshi): This pattern needs dtype promotion.
        return xchainer.testing.ignore()
    return xp.arange(stop, dtype=dtype_spec)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('start,stop', [
    (0, 0),
    (0, 3),
    (-3, 2),
    (2, 0),
    (-2.2, 3.4),
    (True, True),
    (False, False),
    (True, False),
    (False, True),
])
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec', additional_args=(None,))
def test_arange_start_stop(xp, start, stop, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    if _is_bool_spec(dtype_spec) and abs(stop - start) > 2:  # Checked in test_invalid_arange_too_long_bool
        return xchainer.testing.ignore()
    if (isinstance(start, bool) or isinstance(stop, bool)) and dtype_spec is None:
        # TODO(niboshi): This pattern needs dtype promotion.
        return xchainer.testing.ignore()
    return xp.arange(start, stop, dtype=dtype_spec)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('start,stop,step', [
    (0, 3, 1),
    (0, 0, 2),
    (0, 1, 2),
    (3, -1, -2),
    (-1, 3, -2),
    (3., 2., 1.2),
    (2., -1., 1.),
    (1, 4, -1.2),
    # (4, 1, -1.2),  # TODO(niboshi): Fix it (or maybe NumPy bug?)
    (False, True, True),
])
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec', additional_args=(None,))
def test_arange_start_stop_step(xp, start, stop, step, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    if _is_bool_spec(dtype_spec) and abs((stop - start) / step) > 2:  # Checked in test_invalid_arange_too_long_bool
        return xchainer.testing.ignore()
    if (isinstance(start, bool) or isinstance(stop, bool) or isinstance(step, bool)) and dtype_spec is None:
        # TODO(niboshi): This pattern needs dtype promotion.
        return xchainer.testing.ignore()
    return xp.arange(start, stop, step, dtype=dtype_spec)


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_arange_with_device(device):
    def check(*args, **kwargs):
        a = xchainer.arange(*args, device=device, **kwargs)
        b = xchainer.arange(*args, **kwargs)
        _check_device(a, device)
        xchainer.testing.assert_array_equal(a, b)

    check(3)
    check(3, dtype='float32')
    check(0, 3)
    check(0, 3, dtype='float32')
    check(0, 3, 2)
    check(0, 3, 2, dtype='float32')


@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_invalid_arange_too_long_bool(device):
    def check(xp, err):
        with pytest.raises(err):
            xp.arange(3, dtype='bool_')
        with pytest.raises(err):
            xp.arange(1, 4, 1, dtype='bool_')
        # Should not raise since the size is <= 2.
        xp.arange(1, 4, 2, dtype='bool_')

    check(xchainer, xchainer.DtypeError)
    check(numpy, ValueError)


@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_invalid_arange_zero_step(device):
    def check(xp, err):
        with pytest.raises(err):
            xp.arange(1, 3, 0)

    check(xchainer, xchainer.XchainerError)
    check(numpy, ZeroDivisionError)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
@pytest.mark.parametrize('n', [0, 1, 2, 257])
def test_identity(xp, n, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    return xp.identity(n, dtype_spec)


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_identity_with_device(device):
    a = xchainer.identity(3, 'float32', device)
    b = xchainer.identity(3, 'float32')
    _check_device(a, device)
    xchainer.testing.assert_array_equal(a, b)


@xchainer.testing.numpy_xchainer_array_equal(accept_error=(ValueError, xchainer.DimensionError))
@pytest.mark.parametrize('device', ['native:0', 'native:0'])
def test_identity_invalid_negative_n(xp, device):
    xp.identity(-1, 'float32')


@xchainer.testing.numpy_xchainer_array_equal(accept_error=(TypeError,))
@pytest.mark.parametrize('device', ['native:1', 'native:0'])
def test_identity_invalid_n_type(xp, device):
    xp.identity(3.0, 'float32')


# TODO(hvy): Add tests with non-ndarray but array-like inputs when supported.
@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('N,M,k', [
    (0, 0, 0),
    (0, 0, 1),
    (2, 1, -2),
    (2, 1, -1),
    (2, 1, 0),
    (2, 1, 1),
    (2, 1, 2),
    (3, 4, -4),
    (3, 4, -1),
    (3, 4, 1),
    (3, 4, 4),
    (6, 3, 1),
    (6, 3, -1),
    (3, 6, 1),
    (3, 6, -1),
])
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_eye(xp, N, M, k, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    return xp.eye(N, M, k, dtype_spec)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('N,M,k', [
    (3, None, 1),
    (3, 4, None),
    (3, None, None),
])
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_eye_with_default(xp, N, M, k, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name

    if M is None and k is None:
        return xp.eye(N, dtype=dtype_spec)
    elif M is None:
        return xp.eye(N, k=k, dtype=dtype_spec)
    elif k is None:
        return xp.eye(N, M=M, dtype=dtype_spec)
    assert False


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_eye_with_device(device):
    a = xchainer.eye(1, 2, 1, 'float32', device)
    b = xchainer.eye(1, 2, 1, 'float32')
    _check_device(a, device)
    xchainer.testing.assert_array_equal(a, b)


@xchainer.testing.numpy_xchainer_array_equal(accept_error=(ValueError, xchainer.DimensionError))
@pytest.mark.parametrize('N,M', [
    (-1, 2),
    (1, -1),
    (-2, -1),
])
@pytest.mark.parametrize('device', ['native:0', 'native:0'])
def test_eye_invalid_negative_N_M(xp, N, M, device):
    xp.eye(N, M, 1, 'float32')


@xchainer.testing.numpy_xchainer_array_equal(accept_error=(TypeError,))
@pytest.mark.parametrize('N,M,k', [
    (1.0, 2, 1),
    (2, 1.0, 1),
    (2, 3, 1.0),
    (2.0, 1.0, 1),
])
@pytest.mark.parametrize('device', ['native:1', 'native:0'])
def test_eye_invalid_NMk_type(xp, N, M, k, device):
    xp.eye(N, M, k, 'float32')


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('k', [0, -2, -1, 1, 2, -5, 4])
@pytest.mark.parametrize('shape', [(4,), (2, 3), (6, 5)])
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_diag(xp, k, shape, device):
    v = xp.arange(_total_size(shape)).reshape(shape)
    return xp.diag(v, k)


@xchainer.testing.numpy_xchainer_array_equal(accept_error=(ValueError, xchainer.DimensionError))
@pytest.mark.parametrize('k', [0, -2, -1, 1, 2, -5, 4])
@pytest.mark.parametrize('shape', [(), (2, 1, 2), (2, 0, 1)])
@pytest.mark.parametrize('device', ['native:1', 'native:0'])
def test_diag_invalid_ndim(xp, k, shape, device):
    v = xp.arange(_total_size(shape)).reshape(shape)
    return xp.diag(v, k)


# TODO(hvy): Add tests with non-ndarray but array-like inputs when supported.
@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('k', [0, -2, -1, 1, 2, -5, 4])
@pytest.mark.parametrize('shape', [(), (4,), (2, 3), (6, 5), (2, 0)])
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
def test_diagflat(xp, k, shape, device):
    v = xp.arange(_total_size(shape)).reshape(shape)
    return xp.diagflat(v, k)


@xchainer.testing.numpy_xchainer_array_equal(accept_error=(ValueError, xchainer.DimensionError))
@pytest.mark.parametrize('k', [0, -2, -1, 1, 2, -5, 4])
@pytest.mark.parametrize('shape', [(2, 1, 2), (2, 0, 1)])
@pytest.mark.parametrize('device', ['native:1', 'native:0'])
def test_diagflat_invalid_ndim(xp, k, shape, device):
    v = xp.arange(_total_size(shape)).reshape(shape)
    return xp.diagflat(v, k)


@xchainer.testing.numpy_xchainer_allclose()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@pytest.mark.parametrize('start,stop', [
    (0, 0),
    (0, 1),
    (1, 0),
    (-1, 0),
    (0, -1),
    (1, -1),
    (-13.3, 352.5),
    (13.3, -352.5),
])
@pytest.mark.parametrize('num', [0, 1, 2, 257])
@pytest.mark.parametrize('endpoint', [True, False])
@pytest.mark.parametrize('range_type', [float, int])
def test_linspace(xp, start, stop, num, endpoint, range_type, dtype, device):
    start = range_type(start)
    stop = range_type(stop)
    return xp.linspace(start, stop, num, endpoint=endpoint, dtype=dtype)


@xchainer.testing.numpy_xchainer_allclose()
@pytest.mark.parametrize_device(['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_linspace_dtype_spec(xp, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name
    return xp.linspace(3, 5, 10, dtype=dtype_spec)


@pytest.mark.parametrize('device', [None, 'native:1', xchainer.get_device('native:1')])
def test_linspace_with_device(device):
    a = xchainer.linspace(3, 5, 10, dtype='float32', device=device)
    b = xchainer.linspace(3, 5, 10, dtype='float32')
    _check_device(a, device)
    xchainer.testing.assert_array_equal(a, b)


@xchainer.testing.numpy_xchainer_array_equal(accept_error=(ValueError, xchainer.XchainerError))
@pytest.mark.parametrize('device', ['native:0', 'native:0'])
def test_linspace_invalid_num(xp, device):
    xp.linspace(2, 4, -1)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('count', [-1, 0, 2])
@pytest.mark.parametrize('sep', ['', 'a'])
@pytest.mark.parametrize('device', ['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_fromfile(xp, count, sep, dtype_spec, device):
    # Write array data to temporary file.
    if isinstance(dtype_spec, xchainer.dtype):
        numpy_dtype_spec = dtype_spec.name
    else:
        numpy_dtype_spec = dtype_spec
    data = numpy.arange(2, dtype=numpy_dtype_spec)
    f = tempfile.TemporaryFile()
    data.tofile(f, sep=sep)

    # Read file.
    f.seek(0)
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = numpy_dtype_spec
    return xp.fromfile(f, dtype=dtype_spec, count=count, sep=sep)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('device', ['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_loadtxt(xp, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name

    txt = '''// Comment to be ignored.
1 2 3 4
5 6 7 8
'''
    txt = StringIO(txt)

    # Converter that is used to add 1 to each element in the 3rd column.
    def converter(element_str):
        return float(element_str) + 1

    return xp.loadtxt(
        txt, dtype=dtype_spec, comments='//', delimiter=' ', converters={3: converter}, skiprows=2, usecols=(1, 3), unpack=False,
        ndmin=2, encoding='bytes')


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('count', [-1, 0, 5])
@pytest.mark.parametrize('device', ['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_fromiter(xp, count, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name

    iterable = (x * x for x in range(5))
    return xp.fromiter(iterable, dtype=dtype_spec, count=count)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('count', [-1, 0, 3])
@pytest.mark.parametrize('sep', [' ', 'a'])
@pytest.mark.parametrize('device', ['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_fromstring(xp, count, sep, dtype_spec, device):
    if isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name

    elements = ['1', '2', '3']
    string = sep.join(elements)
    return xp.fromstring(string, dtype=dtype_spec, count=count, sep=sep)


@xchainer.testing.numpy_xchainer_array_equal()
@pytest.mark.parametrize('device', ['native:0', 'cuda:0'])
@xchainer.testing.parametrize_dtype_specifier('dtype_spec')
def test_fromfunction(xp, dtype_spec, device):
    if xp is numpy and isinstance(dtype_spec, xchainer.dtype):
        dtype_spec = dtype_spec.name

    def function(i, j, addend):
        return i * j + addend

    # addend should be passed as a keyword argument to function.
    return xp.fromfunction(function, (2, 2), dtype=dtype_spec, addend=2)
