#!/usr/bin/env python
import new

# Make the environment more like Python 3.0
__metaclass__ = type
from itertools import izip as zip
import textwrap
import inspect


__all__ = [
	"AnyType",
	"overloaded"
]


AnyType = object


class overloaded:
	"""
	Dynamically overloaded functions.

	This is an implementation of (dynamically, or run-time) overloaded
	functions; also known as generic functions or multi-methods.

	The dispatch algorithm uses the types of all argument for dispatch,
	similar to (compile-time) overloaded functions or methods in C++ and
	Java.

	Most of the complexity in the algorithm comes from the need to support
	subclasses in call signatures.  For example, if an function is
	registered for a signature (T1, T2), then a call with a signature (S1,
	S2) is acceptable, assuming that S1 is a subclass of T1, S2 a subclass
	of T2, and there are no other more specific matches (see below).

	If there are multiple matches and one of those doesn't *dominate* all
	others, the match is deemed ambiguous and an exception is raised.  A
	subtlety here: if, after removing the dominated matches, there are
	still multiple matches left, but they all map to the same function,
	then the match is not deemed ambiguous and that function is used.
	Read the method find_func() below for details.

	@note Python 2.5 is required due to the use of predicates any() and all().
	@note only supports positional arguments

	@author http://www.artima.com/weblogs/viewpost.jsp?thread=155514

	>>> import misc
	>>> misc.validate_decorator (overloaded)
	>>>
	>>>
	>>>
	>>>
	>>> #################
	>>> #Basics, with reusing names and without
	>>> @overloaded
	... def foo(x):
	... 	"prints x"
	... 	print x
	...
	>>> @foo.register(int)
	... def foo(x):
	... 	"prints the hex representation of x"
	... 	print hex(x)
	...
	>>> from types import DictType
	>>> @foo.register(DictType)
	... def foo_dict(x):
	... 	"prints the keys of x"
	... 	print [k for k in x.iterkeys()]
	...
	>>> #combines all of the doc strings to help keep track of the specializations
	>>> foo.__doc__  # doctest: +ELLIPSIS
	"prints x\\n\\n...overloading.foo (<type 'int'>):\\n\\tprints the hex representation of x\\n\\n...overloading.foo_dict (<type 'dict'>):\\n\\tprints the keys of x"
	>>> foo ("text")
	text
	>>> foo (10) #calling the specialized foo
	0xa
	>>> foo ({3:5, 6:7}) #calling the specialization foo_dict
	[3, 6]
	>>> foo_dict ({3:5, 6:7}) #with using a unique name, you still have the option of calling the function directly
	[3, 6]
	>>>
	>>>
	>>>
	>>>
	>>> #################
	>>> #Multiple arguments, accessing the default, and function finding
	>>> @overloaded
	... def two_arg (x, y):
	... 	print x,y
	...
	>>> @two_arg.register(int, int)
	... def two_arg_int_int (x, y):
	... 	print hex(x), hex(y)
	...
	>>> @two_arg.register(float, int)
	... def two_arg_float_int (x, y):
	... 	print x, hex(y)
	...
	>>> @two_arg.register(int, float)
	... def two_arg_int_float (x, y):
	... 	print hex(x), y
	...
	>>> two_arg.__doc__ # doctest: +ELLIPSIS
	"...overloading.two_arg_int_int (<type 'int'>, <type 'int'>):\\n\\n...overloading.two_arg_float_int (<type 'float'>, <type 'int'>):\\n\\n...overloading.two_arg_int_float (<type 'int'>, <type 'float'>):"
	>>> two_arg(9, 10)
	0x9 0xa
	>>> two_arg(9.0, 10)
	9.0 0xa
	>>> two_arg(15, 16.0)
	0xf 16.0
	>>> two_arg.default_func(9, 10)
	9 10
	>>> two_arg.find_func ((int, float)) == two_arg_int_float
	True
	>>> (int, float) in two_arg
	True
	>>> (str, int) in two_arg
	False
	>>>
	>>>
	>>>
	>>> #################
	>>> #wildcard
	>>> @two_arg.register(AnyType, str)
	... def two_arg_any_str (x, y):
	... 	print x, y.lower()
	...
	>>> two_arg("Hello", "World")
	Hello world
	>>> two_arg(500, "World")
	500 world
	"""

	def __init__(self, default_func):
		# Decorator to declare new overloaded function.
		self.registry = {}
		self.cache = {}
		self.default_func = default_func
		self.__name__ = self.default_func.__name__
		self.__doc__ = self.default_func.__doc__
		self.__dict__.update (self.default_func.__dict__)

	def __get__(self, obj, type=None):
		if obj is None:
			return self
		return new.instancemethod(self, obj)

	def register(self, *types):
		"""
		Decorator to register an implementation for a specific set of types.

		.register(t1, t2)(f) is equivalent to .register_func((t1, t2), f).
		"""

		def helper(func):
			self.register_func(types, func)

			originalDoc = self.__doc__ if self.__doc__ is not None else ""
			typeNames = ", ".join ([str(type) for type in types])
			typeNames = "".join ([func.__module__+".", func.__name__, " (", typeNames, "):"])
			overloadedDoc = ""
			if func.__doc__ is not None:
				overloadedDoc = textwrap.fill (func.__doc__, width=60, initial_indent="\t", subsequent_indent="\t")
			self.__doc__ = "\n".join ([originalDoc, "", typeNames, overloadedDoc]).strip()

			new_func = func

			#Masking the function, so we want to take on its traits
			if func.__name__ == self.__name__:
				self.__dict__.update (func.__dict__)
				new_func = self
			return new_func

		return helper

	def register_func(self, types, func):
		"""Helper to register an implementation."""
		self.registry[tuple(types)] = func
		self.cache = {} # Clear the cache (later we can optimize this).

	def __call__(self, *args):
		"""Call the overloaded function."""
		types = tuple(map(type, args))
		func = self.cache.get(types)
		if func is None:
			self.cache[types] = func = self.find_func(types)
		return func(*args)

	def __contains__ (self, types):
		return self.find_func(types) is not self.default_func

	def find_func(self, types):
		"""Find the appropriate overloaded function; don't call it.

		@note This won't work for old-style classes or classes without __mro__
		"""
		func = self.registry.get(types)
		if func is not None:
			# Easy case -- direct hit in registry.
			return func

		# Phillip Eby suggests to use issubclass() instead of __mro__.
		# There are advantages and disadvantages.

		# I can't help myself -- this is going to be intense functional code.
		# Find all possible candidate signatures.
		mros = tuple(inspect.getmro(t) for t in types)
		n = len(mros)
		candidates = [sig for sig in self.registry
				if len(sig) == n and
					all(t in mro for t, mro in zip(sig, mros))]

		if not candidates:
			# No match at all -- use the default function.
			return self.default_func
		elif len(candidates) == 1:
			# Unique match -- that's an easy case.
			return self.registry[candidates[0]]

		# More than one match -- weed out the subordinate ones.

		def dominates(dom, sub,
				orders=tuple(dict((t, i) for i, t in enumerate(mro))
							for mro in mros)):
			# Predicate to decide whether dom strictly dominates sub.
			# Strict domination is defined as domination without equality.
			# The arguments dom and sub are type tuples of equal length.
			# The orders argument is a precomputed auxiliary data structure
			# giving dicts of ordering information corresponding to the
			# positions in the type tuples.
			# A type d dominates a type s iff order[d] <= order[s].
			# A type tuple (d1, d2, ...) dominates a type tuple of equal length
			# (s1, s2, ...) iff d1 dominates s1, d2 dominates s2, etc.
			if dom is sub:
				return False
			return all(order[d] <= order[s] for d, s, order in zip(dom, sub, orders))

		# I suppose I could inline dominates() but it wouldn't get any clearer.
		candidates = [cand
				for cand in candidates
					if not any(dominates(dom, cand) for dom in candidates)]
		if len(candidates) == 1:
			# There's exactly one candidate left.
			return self.registry[candidates[0]]

		# Perhaps these multiple candidates all have the same implementation?
		funcs = set(self.registry[cand] for cand in candidates)
		if len(funcs) == 1:
			return funcs.pop()

		# No, the situation is irreducibly ambiguous.
		raise TypeError("ambigous call; types=%r; candidates=%r" %
						(types, candidates))
