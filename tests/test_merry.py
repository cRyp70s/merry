from io import StringIO
import logging
import unittest
from merry import Merry


class TestMerry(unittest.TestCase):
    def test_simple_except(self):
        m = Merry()
        m.g.except_called = False

        @m._except(ZeroDivisionError)
        def zerodiv():
            m.g.except_called = True

        @m._try
        def f():
            1/0

        f()
        self.assertTrue(m.g.except_called)

    def test_simple_except2(self):
        m = Merry()
        m.g.except_called = False

        @m._except(ZeroDivisionError)
        def zerodiv(e):
            self.assertIsInstance(e, ZeroDivisionError)
            m.g.except_called = True

        @m._try
        def f():
            1/0

        f()
        self.assertTrue(m.g.except_called)

    def test_except_parent(self):
        m = Merry()
        m.g.except_called = False

        @m._except(Exception)
        def catch_all(e):
            pass

        @m._except(ArithmeticError)
        def arith_error(e):
            self.assertIsInstance(e, ZeroDivisionError)
            m.g.except_called = True

        @m._try
        def f():
            1/0

        f()
        self.assertTrue(m.g.except_called)

    def test_except_finally(self):
        m = Merry()
        m.g.except_called = False
        m.g.else_called = False
        m.g.finally_called = False

        @m._except(ZeroDivisionError)
        def zerodiv(e):
            m.g.except_called = True

        @m._else
        def else_clause():
            m.g.else_called = True

        @m._finally
        def finally_clause():
            m.g.finally_called = True

        @m._try
        def f():
            1/0

        f()
        self.assertTrue(m.g.except_called)
        self.assertFalse(m.g.else_called)
        self.assertTrue(m.g.finally_called)

    def test_else_finally(self):
        m = Merry()
        m.g.except_called = False
        m.g.else_called = False
        m.g.finally_called = False

        @m._except(Exception)
        def catch_all(e):
            pass

        @m._except(ArithmeticError)
        def arith_error(e):
            m.g.except_called = True

        @m._else
        def else_clause():
            m.g.else_called = True

        @m._finally
        def finally_clause():
            m.g.finally_called = True

        @m._try
        def f():
            pass

        f()
        self.assertFalse(m.g.except_called)
        self.assertTrue(m.g.else_called)
        self.assertTrue(m.g.finally_called)

    def test_return_prevents_else(self):
        m = Merry()
        m.g.except_called = False
        m.g.else_called = False
        m.g.finally_called = False

        @m._except(ZeroDivisionError)
        def zerodiv(e):
            m.g.except_called = True

        @m._else
        def else_clause():
            m.g.else_called = True

        @m._finally
        def finally_clause():
            m.g.finally_called = True

        @m._try
        def f():
            return 'foo'

        f()
        self.assertFalse(m.g.except_called)
        self.assertFalse(m.g.else_called)
        self.assertTrue(m.g.finally_called)

    def test_unhandled(self):
        m = Merry()

        @m._try
        def f():
            1/0

        self.assertRaises(ZeroDivisionError, f)

    def test_return_value_if_no_error(self):
        m = Merry()

        @m._try
        def f():
            return 'foo'

        @m._else
        def else_clause():
            return 'bar'

        self.assertEqual(f(), 'foo')

    def test_return_value_from_except(self):
        m = Merry()

        @m._except(ZeroDivisionError)
        def zerodiv():
            return 'foo'

        @m._try
        def f():
            1/0

        self.assertEqual(f(), 'foo')

    def test_return_value_from_else(self):
        m = Merry()

        @m._else
        def else_clause():
            return 'foo'

        @m._try
        def f():
            pass

        self.assertEqual(f(), 'foo')

    def test_return_value_from_finally(self):
        m = Merry()

        @m._try
        def f():
            pass

        @m._finally
        def finally_clause():
            return 'bar'

        self.assertEqual(f(), 'bar')

    def test_return_value_from_finally2(self):
        m = Merry()

        @m._try
        def f():
            return 'foo'

        @m._finally
        def finally_clause():
            return 'bar'

        self.assertEqual(f(), 'bar')

    def test_return_value_from_finally3(self):
        m = Merry()

        @m._try
        def f():
            1/0

        @m._except(ZeroDivisionError)
        def zerodiv():
            return 'foo'

        @m._finally
        def finally_clause():
            return 'bar'

        self.assertEqual(f(), 'bar')

    def test_global_debug(self):
        m = Merry(debug=True)
        m.g.except_called = False

        @m._except(ZeroDivisionError)
        def zerodiv():
            m.g.except_called = True

        @m._try
        def f():
            1/0

        self.assertRaises(ZeroDivisionError, f)
        self.assertFalse(m.g.except_called)

    def test_local_debug(self):
        m = Merry()
        m.g.except_called = False

        @m._except(ZeroDivisionError, debug=True)
        def zerodiv():
            m.g.except_called = True

        @m._try
        def f():
            1/0

        self.assertRaises(ZeroDivisionError, f)
        self.assertFalse(m.g.except_called)

    def test_local_debug_override(self):
        m = Merry(debug=True)
        m.g.except_called = False

        @m._except(ZeroDivisionError, debug=False)
        def zerodiv():
            m.g.except_called = True

        @m._try
        def f():
            1/0

        f()
        self.assertTrue(m.g.except_called)

    def test_logger(self):
        m = Merry()
        m.g.except_called = False
        stream = StringIO()
        m.logger.addHandler(logging.StreamHandler(stream))

        @m._except(ZeroDivisionError)
        def zerodiv():
            m.g.except_called = True

        @m._try
        def f():
            1/0

        f()
        self.assertIn('Traceback', stream.getvalue())
        self.assertIn('ZeroDivisionError: ', stream.getvalue())

    def test_custom_logger(self):
        my_logger = logging.getLogger('foo')
        stream = StringIO()
        my_logger.addHandler(logging.StreamHandler(stream))

        m = Merry(logger_name='foo')
        m.g.except_called = False

        @m._except(ZeroDivisionError)
        def zerodiv():
            m.g.except_called = True

        @m._try
        def f():
            1/0

        f()
        self.assertIn('Traceback', stream.getvalue())
        self.assertIn('ZeroDivisionError: ', stream.getvalue())


if __name__ == '__main__':
    unittest.main()
