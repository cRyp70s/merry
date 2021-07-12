from functools import wraps
import inspect
import logging

getargspec = None
if getattr(inspect, 'getfullargspec', None):
    getargspec = inspect.getfullargspec
else:
    # this one is deprecated in Python 3, but available in Python 2
    getargspec = inspect.getargspec


class _Namespace:
    pass


class Merry(object):
    """Initialze merry.

    :param logger_name: the logger name to use. The default is ``'merry'``.
    :param debug: set to ``True`` to enable debug mode, which causes all
                  errors to bubble up so that a debugger can catch them. The
                  default is ``False``.
    """
    def __init__(self, logger_name='merry', debug=False):
        self.logger = logging.getLogger(logger_name)
        self.g = _Namespace()
        self.debug = debug
        self.except_ = {}
        self.force_debug = []

        # Dictionaries to register handlers for except, else and finally
        # methods. Keys are the function names.
        # Values are exception-handler dictionaries
        self.function_exception_handler_map = {}
        self.function_else_handler_map = {}
        self.function_finally_handler_map = {}
        self.last_try = None
        self.force_handle = []
        self.else_ = None
        self.finally_ = None

    def _try(self, f):
        """Decorator that wraps a function in a try block.

        Example usage::

            @merry._try
            def my_function():
                # do something here
        """
        name = f.__name__
        if name not in self.function_exception_handler_map:
            self.function_exception_handler_map[name] = {}
        if name not in self.function_else_handler_map:
            self.function_else_handler_map[name] = None
        if name not in self.function_finally_handler_map:
            self.function_finally_handler_map[name] = None
        self.last_try = name

        @wraps(f)
        def wrapper(*args, **kwargs):
            ret = None
            try:
                ret = f(*args, **kwargs)

                # note that if the function returned something, the else clause
                # will be skipped. This is a similar behavior to a normal
                # try/except/else block.
                if ret is not None:
                    return ret
            except Exception as e: 

                # If an handler hasn't been registered for the function create
                # a dictionary for the function.

                self.except_ = self.function_exception_handler_map[name]
                self.else_ = self.function_else_handler_map[name]
                self.finally_ = self.function_finally_handler_map[name]

                # find the best handler for this exception
                handler = None
                for c in self.except_.keys():
                    if isinstance(e, c):
                        if handler is None or issubclass(c, handler):
                            handler = c

                # if we don't have any handler, we let the exception bubble up
                if handler is None:
                    raise e

                # log exception
                self.logger.exception('[merry] Exception caught')

                # if in debug mode, then bubble up to let a debugger handle
                debug = self.debug
                if handler in self.force_debug:
                    debug = True
                elif handler in self.force_handle:
                    debug = False
                if debug:
                    raise e

                # invoke handler
                if len(getargspec(self.except_[handler])[0]) == 0:
                    return self.except_[handler]()
                else:
                    return self.except_[handler](e)
            else:
                # if we have an else handler, call it now
                if self.else_ is not None:
                    return self.else_()
            finally:
                # if we have a finally handler, call it now
                if self.finally_ is not None:
                    alt_ret = self.finally_()
                    if alt_ret is not None:
                        ret = alt_ret
                    return ret
        return wrapper

    def _except(self, *args, **kwargs):
        """Decorator that registers a function as an error handler for one or
        more exception classes.

        Example usage::

            @merry._except(RuntimeError)
            def runtime_error_handler(e):
                print('runtime error:', str(e))

        :param args: the list of exception classes to be handled by the
                     decorated function.
        :param kwargs: configuration arguments. Pass ``debug=True`` to enable
                       debug mode for this handler, which bubbles up all
                       exceptions. Pass ``debug=False`` to prevent the error
                       from bubbling up, even if debug mode is enabled
                       globally.
                       Pass the ``for_`` argument to  register the handler for
                       a function with name specified as the argument value.
                       The value must be a string or the function that was 
                       registered with the _try decorator.
                       note that the function must have been decorated with a
                       _try decorator.
        """
        def decorator(f):
            for_ = kwargs.get('for_')
            if callable(for_):
                for_ = for_.__name__
            if self.last_try is None and not for_:
                raise Exception("_except decorator must be used after a _try \
                    decorator has been used or 'for_' keyword argument must be\
                     specified with the function name as the value.")

            if for_:
                for e in args:
                    if for_ in self.function_exception_handler_map:
                        self.function_exception_handler_map[for_][e] = f
                    else:
                        raise Exception(for_ + " does not exist or has not been \
                            decorated with _try decorator")
            else:
                for e in args:
                    self.function_exception_handler_map[self.last_try][e] = f
            d = kwargs.get('debug', None)
            if d:
                self.force_debug.append(e)
            elif d is not None:
                self.force_handle.append(e)
            return f
        return decorator

    def _else_for(self, for_):
        """Decorator to define the ``else`` clause handler.
        
        Example usage::

            @merry._else_for('do_something')
            def else_handler():
                print('no exceptions were raised')

        :param for_: Register the handler for a function with name specified 
                     as the argument value.
                     The value must be a string or the function that was 
                     registered with the _try decorator.
                     note that the function must have been decorated with a
                     _try decorator.
        """
        def inner(f):
            if callable(for_):
                for_ = for_.__name__
            if for_ in self.function_else_handler_map:
                self.function_else_handler_map[for_][e] = f
            else:
                raise Exception(for_ + " does not exist or has not been \
                        decorated with _try decorator")
            self.function_else_handler_map[self.last_try] = f
            return f
        return inner

    def _else(self, f):
        """Decorator to define the ``else`` clause handler.
        
        Example usage::

            @merry._else
            def else_handler():
                print('no exceptions were raised')
        """
        if self.last_try is None:
            raise Exception("_else decorator must be used after a _try \
                decorator has been used.")
        self.function_else_handler_map[self.last_try] = f
        return f

    def _finally_for(self, for_):
        """Decorator to define the ``finally`` clause handler.

        Example usage::

            @merry._finally_for('do_something')
            def finally_handler():
                print('clean up')

        :param for_: Register the handler for a function with name specified 
                     as the argument value.
                     The value must be a string or the function that was 
                     registered with the _try decorator.
                     note that the function must have been decorated with a
                     _try decorator.
        """
        def inner(f):
            if callable(for_):
                for_ = for_.__name__
            if for_ in self.function_finally_handler_map:
                self.function_finally_handler_map[for_][e] = f
            else:
                raise Exception(for_ + " does not exist or has not been \
                    decorated with _try decorator")
            self.function_finally_handler_map[self.last_try] = f
            return f
        return inner

    def _finally(self, f):
        """Decorator to define the ``finally`` clause handler.

        Example usage::

            @merry._finally
            def finally_handler():
                print('clean up')
        """
        if self.last_try is None:
            raise Exception("_finally decorator must be used after a _try \
                decorator has been used.")
        self.function_finally_handler_map[self.last_try] = f
        return f
