from __future__ import absolute_import

import ast
import os
import shutil
import tempfile
import unittest

import khodemod
import slicker
import util


class TestBase(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tmpdir = os.path.realpath(
            tempfile.mkdtemp(prefix=(self.__class__.__name__ + '.')))
        self.error_output = []
        # Poor-man's mock.
        self._old_emit = khodemod.emit
        khodemod.emit = lambda txt: self.error_output.append(txt)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        khodemod.emit = self._old_emit

    def join(self, *args):
        return os.path.join(self.tmpdir, *args)

    def copy_file(self, filename):
        """Copy a file from testdata to tmpdir."""
        shutil.copyfile(os.path.join('testdata', filename),
                        os.path.join(self.tmpdir, filename))

    def write_file(self, filename, contents):
        if not os.path.exists(self.join(os.path.dirname(filename))):
            os.makedirs(os.path.dirname(self.join(filename)))
        with open(self.join(filename), 'w') as f:
            f.write(contents)

    def assertFileIs(self, filename, expected):
        with open(self.join(filename)) as f:
            actual = f.read()
        self.assertMultiLineEqual(expected, actual)

    def assertFileIsNot(self, filename):
        self.assertFalse(os.path.exists(self.join(filename)))


class DetermineLocalnamesTest(unittest.TestCase):
    def _assert_localnames(self, actual, expected):
        """Assert imports match the given tuples, but with certain changes."""
        modified_actual = set()
        for localname in actual:
            self.assertIsInstance(localname, slicker.LocalName)
            fullname, ln, imp = localname
            if imp is None:
                modified_actual.add((fullname, ln, None))
            else:
                self.assertIsInstance(imp, slicker.Import)
                (name, alias, start, end, node) = imp
                self.assertIsInstance(node, (ast.Import, ast.ImportFrom))
                modified_actual.add(
                    (fullname, ln, (name, alias, start, end)))
        self.assertEqual(modified_actual, expected)

    # TODO(benkraft): Move some of this to a separate ComputeAllImportsTest.
    def test_simple(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo', util.File('some_file.py', 'import foo\n')),
            {('foo', 'foo', ('foo', 'foo', 0, 10))})

    def test_with_dots(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'import foo.bar.baz\n')),
            {('foo.bar.baz', 'foo.bar.baz',
              ('foo.bar.baz', 'foo.bar.baz', 0, 18))})

    def test_from_import(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'from foo.bar import baz\n')),
            {('foo.bar.baz', 'baz', ('foo.bar.baz', 'baz', 0, 23))})

    def test_implicit_import(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz', util.File('some_file.py', 'import foo\n')),
            {('foo.bar.baz', 'foo.bar.baz', ('foo', 'foo', 0, 10))})
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'import foo.quux\n')),
            {('foo.bar.baz', 'foo.bar.baz', ('foo.quux', 'foo.quux', 0, 15))})
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'import foo.bar\n')),
            {('foo.bar.baz', 'foo.bar.baz', ('foo.bar', 'foo.bar', 0, 14))})
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'import foo.bar.quux\n')),
            {('foo.bar.baz', 'foo.bar.baz',
              ('foo.bar.quux', 'foo.bar.quux', 0, 19))})
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'import foo.bar.baz.quux\n')),
            {('foo.bar.baz', 'foo.bar.baz',
              ('foo.bar.baz.quux', 'foo.bar.baz.quux', 0, 23))})

    def test_implicit_from_import(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'from foo.bar import quux\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'from foo import bar\n')),
            {('foo.bar.baz', 'bar.baz', ('foo.bar', 'bar', 0, 19))})

    def test_as_import(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo', util.File('some_file.py', 'import foo as bar\n')),
            {('foo', 'bar', ('foo', 'bar', 0, 17))})
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'import foo.bar.baz as quux\n')),
            {('foo.bar.baz', 'quux', ('foo.bar.baz', 'quux', 0, 26))})
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py',
                          'from foo.bar import baz as quux\n')),
            {('foo.bar.baz', 'quux', ('foo.bar.baz', 'quux', 0, 31))})

    def test_implicit_as_import(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'import foo as quux\n')),
            {('foo.bar.baz', 'quux.bar.baz', ('foo', 'quux', 0, 18))})
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'import foo.bar as quux\n')),
            {('foo.bar.baz', 'quux.baz', ('foo.bar', 'quux', 0, 22))})
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py',
                          'import foo.bar.quux as bogus\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'from foo import bar as quux\n')),
            {('foo.bar.baz', 'quux.baz', ('foo.bar', 'quux', 0, 27))})
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py',
                          'from foo.bar import quux as bogus\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py',
                          'import foo.bar.baz.quux as bogus\n')),
            set())

    def test_other_imports(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo', util.File('some_file.py', 'import bogus\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'import bogus.foo.bar.baz\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo',
                util.File('some_file.py', 'from bogus import foo\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'from bogus import foo\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'from bogus import foo, bar\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py',
                          'from foo.bogus import bar, baz\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py', 'import bar, baz\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File('some_file.py',
                          'import bar as foo, baz as quux\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo',
                util.File('some_file.py',
                          'import bogus  # (with a comment)\n')),
            set())

    def test_other_junk(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo', util.File('some_file.py', '# import foo\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo',
                util.File('some_file.py',
                          '                  # import foo\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo', util.File('some_file.py', 'def foo(): pass\n')),
            set())
        self._assert_localnames(
            slicker._determine_localnames(
                'foo',
                util.File('some_file.py',
                          '"""imports are "fun" in a multiline string"""')),
            set())

    def test_with_context(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo',
                util.File(
                    'some_file.py',
                    ('# import foo as bar\n'
                     'import os\n'
                     'import sys\n'
                     '\n'
                     'import bogus\n'
                     'import foo\n'
                     '\n'
                     'def foo():\n'
                     '    return 1\n'))),
            {('foo', 'foo', ('foo', 'foo', 55, 65))})

    def test_multiple_imports(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.baz',
                util.File(
                    'some_file.py',
                    ('import foo\n'
                     'import foo.bar.baz\n'
                     'from foo.bar import baz\n'
                     'import foo.quux\n'))),
            {('foo.bar.baz', 'foo.bar.baz', ('foo', 'foo', 0, 10)),
             ('foo.bar.baz', 'foo.bar.baz',
              ('foo.bar.baz', 'foo.bar.baz', 11, 29)),
             ('foo.bar.baz', 'baz', ('foo.bar.baz', 'baz', 30, 53)),
             ('foo.bar.baz', 'foo.bar.baz', ('foo.quux', 'foo.quux', 54, 69))})

    def test_defined_in_this_file(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo.bar.some_function',
                util.File(
                    'foo/bar.py',
                    'import baz\n'
                    'def f():\n'
                    '    some_function(baz.quux)\n')),
            {('foo.bar.some_function', 'some_function', None)})

    def test_late_import(self):
        self._assert_localnames(
            slicker._determine_localnames(
                'foo', util.File(
                    'some_file.py',
                    ('def f():\n'
                     '    import foo\n'))),
            {('foo', 'foo', ('foo', 'foo', 13, 23))})

        self._assert_localnames(
            slicker._determine_localnames(
                'foo', util.File(
                    'some_file.py',
                    ('def f():\n'
                     '    import foo\n')),
                toplevel_only=True),
            set())

    def test_within_node(self):
        file_info = util.File(
            'some_file.py',
            ('import foo\n\n\n'
             'def f():\n'
             '    import foo as bar\n'))
        def_node = file_info.tree.body[1]

        self._assert_localnames(
            slicker._determine_localnames('foo', file_info),
            {('foo', 'foo', ('foo', 'foo', 0, 10)),
             ('foo', 'bar', ('foo', 'bar', 26, 43))})
        self._assert_localnames(
            slicker._determine_localnames('foo', file_info,
                                          within_node=def_node),
            {('foo', 'bar', ('foo', 'bar', 26, 43))})


class DottedPrefixTest(unittest.TestCase):
    def test_dotted_starts_with(self):
        self.assertTrue(slicker._dotted_starts_with('abc', 'abc'))
        self.assertTrue(slicker._dotted_starts_with('abc.de', 'abc'))
        self.assertTrue(slicker._dotted_starts_with('abc.de', 'abc.de'))
        self.assertTrue(slicker._dotted_starts_with('abc.de.fg', 'abc'))
        self.assertTrue(slicker._dotted_starts_with('abc.de.fg', 'abc.de'))
        self.assertTrue(slicker._dotted_starts_with('abc.de.fg', 'abc.de.fg'))
        self.assertFalse(slicker._dotted_starts_with('abc', 'd'))
        self.assertFalse(slicker._dotted_starts_with('abc', 'ab'))
        self.assertFalse(slicker._dotted_starts_with('abc', 'abc.de'))
        self.assertFalse(slicker._dotted_starts_with('abc.de', 'ab'))
        self.assertFalse(slicker._dotted_starts_with('abc.de', 'abc.d'))
        self.assertFalse(slicker._dotted_starts_with('abc.de', 'abc.h'))

    def test_dotted_prefixes(self):
        self.assertItemsEqual(
            slicker._dotted_prefixes('abc'),
            ['abc'])
        self.assertItemsEqual(
            slicker._dotted_prefixes('abc.def'),
            ['abc', 'abc.def'])
        self.assertItemsEqual(
            slicker._dotted_prefixes('abc.def.ghi'),
            ['abc', 'abc.def', 'abc.def.ghi'])


class NamesStartingWithTest(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(
            set(slicker._names_starting_with('a', ast.parse('a\n'))),
            {'a'})
        self.assertEqual(
            set(slicker._names_starting_with(
                'a', ast.parse('a.b.c\n'))),
            {'a.b.c'})
        self.assertEqual(
            set(slicker._names_starting_with(
                'a', ast.parse('d.e.f\n'))),
            set())

        self.assertEqual(
            set(slicker._names_starting_with(
                'abc', ast.parse('abc.de\n'))),
            {'abc.de'})
        self.assertEqual(
            set(slicker._names_starting_with(
                'ab', ast.parse('abc.de\n'))),
            set())

        self.assertEqual(
            set(slicker._names_starting_with(
                'a', ast.parse('"a.b.c"\n'))),
            set())
        self.assertEqual(
            set(slicker._names_starting_with(
                'a', ast.parse('import a.b.c\n'))),
            set())
        self.assertEqual(
            set(slicker._names_starting_with(
                'a', ast.parse('b.c.a.b.c\n'))),
            set())

    def test_in_context(self):
        self.assertEqual(
            set(slicker._names_starting_with('a', ast.parse(
                'def abc():\n'
                '    if a.b == a.c:\n'
                '        return a.d(a.e + a.f)\n'
                'abc(a.g)\n'))),
            {'a.b', 'a.c', 'a.d', 'a.e', 'a.f', 'a.g'})


class RootTest(TestBase):
    def test_root(self):
        self.copy_file('simple_in.py')
        with open(self.join('foo.py'), 'w') as f:
            print >>f, "def some_function(): return 4"

        slicker.make_fixes('foo.some_function', 'bar.new_name',
                           project_root=self.tmpdir)

        with open(self.join('simple_in.py')) as f:
            actual_body = f.read()
        with open('testdata/simple_out.py') as f:
            expected_body = f.read()
        self.assertMultiLineEqual(expected_body, actual_body)
        self.assertFalse(self.error_output)


class FixUsesTest(TestBase):
    def run_test(self, filebase, old_fullname, new_fullname,
                 import_alias=None,
                 expected_warnings=(), expected_error=None):
        if expected_error:
            expected = None
        else:
            with open('testdata/%s_out.py' % filebase) as f:
                expected = f.read()

        self.copy_file('%s_in.py' % filebase)

        slicker.make_fixes(old_fullname, new_fullname,
                           import_alias, project_root=self.tmpdir,
                           # Since we just create placeholder files for the
                           # moved symbol, we won't be able to find it,
                           # which introduces a spurious error.
                           automove=False)

        with open(self.join('%s_in.py' % filebase)) as f:
            actual = f.read()

        # Assert about the errors first, because they may be more informative.
        if expected_warnings:
            self.assertItemsEqual(expected_warnings, self.error_output)
        elif expected:
            self.assertFalse(self.error_output)

        if expected:
            self.assertMultiLineEqual(expected, actual)
        else:
            self.assertItemsEqual([expected_error], self.error_output)

    def create_module(self, module_name):
        abspath = self.join(module_name.replace('.', os.sep) + '.py')
        if not os.path.exists(os.path.dirname(abspath)):
            os.makedirs(os.path.dirname(abspath))
        with open(abspath, 'w') as f:
            print >>f, "# A file"

    def test_simple(self):
        self.create_module('foo')
        self.run_test(
            'simple',
            'foo.some_function', 'bar.new_name')

    def test_whole_file(self):
        self.create_module('foo')
        self.run_test(
            'whole_file',
            'foo', 'bar')

    def test_whole_file_alias(self):
        self.create_module('foo')
        self.run_test(
            'whole_file_alias',
            'foo', 'bar', import_alias='baz')

    def test_same_prefix(self):
        self.create_module('foo.bar')
        self.run_test(
            'same_prefix',
            'foo.bar.some_function', 'foo.baz.some_function')

    @unittest.skip("TODO(benkraft): We shouldn't consider this a conflict.")
    def test_same_alias(self):
        self.create_module('foo')
        self.run_test(
            'same_alias',
            'foo.some_function', 'bar.some_function', import_alias='foo')

    def test_implicit(self):
        self.create_module('foo.bar.baz')
        self.run_test(
            'implicit',
            'foo.bar.baz.some_function', 'quux.new_name',
            expected_warnings=[
                'WARNING:This import may be used implicitly.\n'
                '    on implicit_in.py:2 --> import foo.bar.baz'])

    def test_double_implicit(self):
        self.create_module('foo.bar.baz')
        self.run_test(
            'double_implicit',
            'foo.bar.baz.some_function', 'quux.new_name')

    def test_moving_implicit(self):
        self.create_module('foo.secrets')
        self.run_test(
            'moving_implicit',
            'foo.secrets.lulz', 'quux.new_name')

    def test_slicker(self):
        """Test on (a perhaps out of date version of) slicker itself.

        It doesn't do anything super fancy, but it's a decent-sized file at
        least.
        """
        self.create_module('codemod')
        self.run_test(
            'slicker',
            'codemod', 'codemod_fork',
            import_alias='the_other_codemod')

    def test_linebreaks(self):
        self.create_module('foo.bar.baz')
        self.run_test(
            'linebreaks',
            'foo.bar.baz.some_function', 'quux.new_name')

    def test_conflict(self):
        self.create_module('foo.bar')
        self.run_test(
            'conflict',
            'foo.bar.interesting_function', 'bar.interesting_function',
            import_alias='foo',
            expected_error=(
                'ERROR:Your alias will conflict with imports in this file.\n'
                '    on conflict_in.py:1 --> import foo.bar'))

    def test_conflict_2(self):
        self.create_module('bar')
        self.run_test(
            'conflict_2',
            'bar.interesting_function', 'foo.bar.interesting_function',
            expected_error=(
                'ERROR:Your alias will conflict with imports in this file.\n'
                '    on conflict_2_in.py:1 --> import quux as foo'))

    def test_unused(self):
        self.create_module('foo.bar')
        self.run_test(
            'unused',
            'foo.bar.some_function', 'quux.some_function',
            expected_warnings=[
                'WARNING:Not removing import with @Nolint.\n'
                '    on unused_in.py:3 --> import foo.baz  # @UnusedImport'])

    def test_many_imports(self):
        self.create_module('foo.quux')
        self.run_test(
            'many_imports',
            'foo.quux.replaceme', 'baz.replaced')

    def test_late_import(self):
        self.create_module('foo.bar')
        self.run_test(
            'late_import',
            'foo.bar.some_function', 'quux.some_function')

    def test_mock(self):
        self.create_module('foo.bar')
        self.run_test(
            'mock',
            'foo.bar.some_function', 'quux.some_function')

    def test_comments(self):
        self.create_module('foo.bar')
        self.run_test(
            'comments',
            'foo.bar.some_function', 'quux.mod.some_function',
            import_alias='al')

    def test_comments_whole_file(self):
        self.create_module('foo.bar')
        self.run_test(
            'comments_whole_file',
            'foo.bar', 'quux.mod', import_alias='al')

    def test_source_file(self):
        """Test fixing up uses in the source of the move itself.

        In this case, we need to add an import.
        """
        self.run_test(
            'source_file',
            'source_file_in.myfunc', 'somewhere_else.myfunc')

    def test_source_file_2(self):
        """Test fixing up uses in the source of the move itself.

        In this case, there is an existing import.
        """
        self.run_test(
            'source_file_2',
            'source_file_2_in.myfunc', 'somewhere_else.myfunc')

    def test_destination_file(self):
        """Test fixing up uses in the destination of the move itself.

        In this case, we remove the import, since this is the only reference.
        """
        self.create_module('somewhere_else')
        self.run_test(
            'destination_file',
            'somewhere_else.myfunc', 'destination_file_in.myfunc')

    def test_destination_file_2(self):
        """Test fixing up uses in the destination of the move itself.

        In this case, we don't remove the import; it has other references.
        """
        self.create_module('somewhere_else')
        self.run_test(
            'destination_file_2',
            'somewhere_else.myfunc', 'destination_file_2_in.myfunc')


class FixMovedRegionSuggestorTest(TestBase):
    # TODO(benkraft): In many cases (mostly noted below), we should remove
    # imports, but don't yet.
    def test_rename_references_self(self):
        self.write_file('foo.py',
                        ('something = 1\n'
                         'def fib(n):\n'
                         '    return fib(n - 1) + fib(n - 2)\n'))
        slicker.make_fixes('foo.fib', 'foo.slow_fib',
                           project_root=self.tmpdir)
        self.assertFileIs('foo.py',
                          ('something = 1\n'
                           'def slow_fib(n):\n'
                           '    return slow_fib(n - 1) + slow_fib(n - 2)\n'))
        self.assertFalse(self.error_output)

    def test_move_references_self(self):
        self.write_file('foo.py',
                        ('something = 1\n'
                         'def fib(n):\n'
                         '    return fib(n - 1) + fib(n - 2)\n'))
        slicker.make_fixes('foo.fib', 'newfoo.fib',
                           project_root=self.tmpdir)
        self.assertFileIs('foo.py',
                          'something = 1\n')
        self.assertFileIs('newfoo.py',
                          ('def fib(n):\n'
                           '    return fib(n - 1) + fib(n - 2)\n'))
        self.assertFalse(self.error_output)

    def test_rename_and_move_references_self(self):
        self.write_file('foo.py',
                        ('something = 1\n'
                         'def fib(n):\n'
                         '    return fib(n - 1) + fib(n - 2)\n'))
        slicker.make_fixes('foo.fib', 'newfoo.slow_fib',
                           project_root=self.tmpdir)
        self.assertFileIs('foo.py',
                          'something = 1\n')
        self.assertFileIs('newfoo.py',
                          ('def slow_fib(n):\n'
                           '    return slow_fib(n - 1) + slow_fib(n - 2)\n'))
        self.assertFalse(self.error_output)

    def test_references_old_module(self):
        self.write_file('foo.py',
                        ('const = 1\n\n\n'
                         'def f():\n'
                         '    pass\n\n\n'
                         'def myfunc():\n'
                         '    return f(const)\n'))
        slicker.make_fixes('foo.myfunc', 'newfoo.myfunc',
                           project_root=self.tmpdir)
        self.assertFileIs('foo.py',
                          ('const = 1\n\n\n'
                           'def f():\n'
                           '    pass\n'))
        self.assertFileIs('newfoo.py',
                          ('from __future__ import absolute_import\n\n'
                           'import foo\n\n\n'
                           'def myfunc():\n'
                           '    return foo.f(foo.const)\n'))
        self.assertFalse(self.error_output)

    def test_references_old_module_already_imported(self):
        self.write_file('foo.py',
                        ('const = 1\n\n\n'
                         'def f():\n'
                         '    pass\n\n\n'
                         'def myfunc():\n'
                         '    return f(const)\n'))
        self.write_file('newfoo.py',
                        ('from __future__ import absolute_import\n\n'
                         'import foo\n\n\n'
                         'def f():\n'
                         '    return foo.f()\n'))

        slicker.make_fixes('foo.myfunc', 'newfoo.myfunc',
                           project_root=self.tmpdir)
        self.assertFileIs('foo.py',
                          ('const = 1\n\n\n'
                           'def f():\n'
                           '    pass\n'))
        self.assertFileIs('newfoo.py',
                          ('from __future__ import absolute_import\n\n'
                           'import foo\n\n\n'
                           'def f():\n'
                           '    return foo.f()\n\n\n'
                           'def myfunc():\n'
                           '    return foo.f(foo.const)\n'))
        self.assertFalse(self.error_output)

    def test_references_old_module_imports_self(self):
        self.write_file('foo.py',
                        ('import foo\n\n\n'
                         'const = 1\n\n\n'
                         'def f(x):\n'
                         '    pass\n\n\n'
                         'def myfunc():\n'
                         '    return foo.f(foo.const)\n'))
        slicker.make_fixes('foo.myfunc', 'newfoo.myfunc',
                           project_root=self.tmpdir)
        self.assertFileIs('foo.py',
                          ('import foo\n\n\n'  # TODO(benkraft): remove
                           'const = 1\n\n\n'
                           'def f(x):\n'
                           '    pass\n'))
        self.assertFileIs('newfoo.py',
                          ('from __future__ import absolute_import\n\n'
                           'import foo\n\n\n'
                           'def myfunc():\n'
                           '    return foo.f(foo.const)\n'))
        self.assertFalse(self.error_output)

    def test_references_new_module(self):
        self.write_file('foo.py',
                        ('import newfoo\n\n\n'
                         'def myfunc():\n'
                         '    return newfoo.f(newfoo.const)\n'))
        self.write_file('newfoo.py',
                        ('const = 1\n\n\n'
                         'def f(x):\n'
                         '    pass\n'))
        slicker.make_fixes('foo.myfunc', 'newfoo.myfunc',
                           project_root=self.tmpdir)
        # TODO(benkraft): remove last import and file
        # self.assertFileIsNot('foo.py')
        self.assertFileIs('newfoo.py',
                          ('const = 1\n\n\n'
                           'def f(x):\n'
                           '    pass\n\n\n'
                           'def myfunc():\n'
                           '    return f(const)\n'))
        self.assertFalse(self.error_output)

    def test_references_new_module_via_alias(self):
        self.write_file('foo.py',
                        ('import newfoo as bar\n\n\n'
                         'def myfunc():\n'
                         '    return bar.f(bar.const)\n'))
        self.write_file('newfoo.py',
                        ('const = 1\n\n\n'
                         'def f(x):\n'
                         '    pass\n'))
        slicker.make_fixes('foo.myfunc', 'newfoo.myfunc',
                           project_root=self.tmpdir)
        # TODO(benkraft): remove last import and file
        # self.assertFileIsNot('foo.py')
        self.assertFileIs('newfoo.py',
                          ('const = 1\n\n\n'
                           'def f(x):\n'
                           '    pass\n\n\n'
                           'def myfunc():\n'
                           '    return f(const)\n'))
        self.assertFalse(self.error_output)

    def test_references_new_module_via_symbol_import(self):
        self.write_file('foo.py',
                        ('from newfoo import const\n'
                         'from newfoo import f\n\n\n'
                         'def myfunc():\n'
                         '    return f(const)\n'))
        self.write_file('newfoo.py',
                        ('const = 1\n\n\n'
                         'def f():\n'
                         '    pass\n'))
        slicker.make_fixes('foo.myfunc', 'newfoo.myfunc',
                           project_root=self.tmpdir)
        # TODO(benkraft): remove last import and file
        # self.assertFileIsNot('foo.py')
        self.assertFileIs('newfoo.py',
                          ('const = 1\n\n\n'
                           'def f():\n'
                           '    pass\n\n\n'
                           'def myfunc():\n'
                           '    return f(const)\n'))
        self.assertFalse(self.error_output)

    def test_references_new_module_imports_self(self):
        self.write_file('foo.py',
                        ('import newfoo\n\n\n'
                         'def myfunc():\n'
                         '    return newfoo.f(newfoo.const)\n'))
        self.write_file('newfoo.py',
                        ('import newfoo\n\n\n'
                         'const = 1\n\n\n'
                         'def f(x):\n'
                         '    return newfoo.const\n'))
        slicker.make_fixes('foo.myfunc', 'newfoo.myfunc',
                           project_root=self.tmpdir)
        # TODO(benkraft): remove last import and file
        # self.assertFileIsNot('foo.py')
        self.assertFileIs('newfoo.py',
                          ('import newfoo\n\n\n'
                           'const = 1\n\n\n'
                           'def f(x):\n'
                           '    return newfoo.const\n\n\n'
                           'def myfunc():\n'
                           '    return f(const)\n'))
        self.assertFalse(self.error_output)

    def test_move_references_everything_in_sight(self):
        self.write_file('foo.py',
                        ('import newfoo\n\n\n'
                         'def f(x):\n'
                         '    pass\n\n\n'
                         'def myfunc(n):\n'
                         '    return myfunc(n-1) + f(newfoo.const)\n'))
        self.write_file('newfoo.py',
                        ('const = 1\n'))
        slicker.make_fixes('foo.myfunc', 'newfoo.myfunc',
                           project_root=self.tmpdir)
        self.assertFileIs('foo.py',
                          ('import newfoo\n\n\n'  # TODO(benkraft): remove
                           'def f(x):\n'
                           '    pass\n'))
        self.assertFileIs('newfoo.py',
                          ('from __future__ import absolute_import\n\n'
                           'import foo\n\n\n'
                           'const = 1\n\n\n'
                           'def myfunc(n):\n'
                           '    return myfunc(n-1) + foo.f(const)\n'))

    def test_rename_and_move_references_everything_in_sight(self):
        self.write_file('foo.py',
                        ('import newfoo\n\n\n'
                         'def f(x):\n'
                         '    pass\n\n\n'
                         'def myfunc(n):\n'
                         '    return myfunc(n-1) + f(newfoo.const)\n'))
        self.write_file('newfoo.py',
                        ('const = 1\n'))
        slicker.make_fixes('foo.myfunc', 'newfoo.mynewerfunc',
                           project_root=self.tmpdir)
        self.assertFileIs('foo.py',
                          ('import newfoo\n\n\n'  # TODO(benkraft): remove
                           'def f(x):\n'
                           '    pass\n'))
        self.assertFileIs('newfoo.py',
                          ('from __future__ import absolute_import\n\n'
                           'import foo\n\n\n'
                           'const = 1\n\n\n'
                           'def mynewerfunc(n):\n'
                           '    return mynewerfunc(n-1) + foo.f(const)\n'))

    def test_move_references_same_name_in_both(self):
        self.write_file('foo.py',
                        ('import newfoo\n\n\n'
                         'def f(g):\n'
                         '    return g(1)\n\n\n'
                         'def myfunc(n):\n'
                         '    return f(newfoo.f)\n'))
        self.write_file('newfoo.py',
                        ('const = 1\n\n\n'
                         'def f(x):\n'
                         '    return x\n'))
        slicker.make_fixes('foo.myfunc', 'newfoo.myfunc',
                           project_root=self.tmpdir)
        self.assertFileIs('foo.py',
                          ('import newfoo\n\n\n'  # TODO(benkraft): remove
                           'def f(g):\n'
                           '    return g(1)\n'))
        self.assertFileIs('newfoo.py',
                          ('from __future__ import absolute_import\n\n'
                           'import foo\n\n\n'
                           'const = 1\n\n\n'
                           'def f(x):\n'
                           '    return x\n\n\n'
                           'def myfunc(n):\n'
                           '    return foo.f(f)\n'))

    def test_late_import_in_moved_region(self):
        self.write_file('foo.py',
                        ('def myfunc():\n'
                         '    import newfoo\n'
                         '    return newfoo.const\n'))
        self.write_file('newfoo.py',
                        ('const = 1\n'))
        slicker.make_fixes('foo.myfunc', 'newfoo.myfunc',
                           project_root=self.tmpdir)
        self.assertFileIsNot('foo.py')
        self.assertFileIs('newfoo.py',
                          ('const = 1\n\n\n'
                           'def myfunc():\n'
                           '    import newfoo\n'  # TODO(benkraft): remove
                           '    return const\n'))

    def test_late_import_elsewhere(self):
        self.write_file('foo.py',
                        ('def f():\n'
                         '    import newfoo\n'
                         '    return newfoo.const\n\n\n'
                         'def myfunc():\n'
                         '    import newfoo\n'
                         '    return newfoo.const\n'))
        self.write_file('newfoo.py',
                        ('const = 1\n'))
        slicker.make_fixes('foo.myfunc', 'newfoo.myfunc',
                           project_root=self.tmpdir)
        self.assertFileIs('foo.py',
                          ('def f():\n'
                           '    import newfoo\n'
                           '    return newfoo.const\n'))
        self.assertFileIs('newfoo.py',
                          ('const = 1\n\n\n'
                           'def myfunc():\n'
                           '    import newfoo\n'  # TODO(benkraft): remove
                           '    return const\n'))


class ImportSortTest(TestBase):
    def test_third_party_sorting(self):
        self.copy_file('third_party_sorting_in.py')

        os.mkdir(self.join('third_party'))
        for f in ('mycode1.py', 'mycode2.py',
                  'third_party/__init__.py', 'third_party/slicker.py'):
            with open(self.join(f), 'w') as f:
                print >>f, '# A file'

        slicker.make_fixes('third_party_sorting_in', 'out',
                           project_root=self.tmpdir)

        with open(self.join('out.py')) as f:
            actual = f.read()
        with open('testdata/third_party_sorting_out.py') as f:
            expected = f.read()
        self.assertMultiLineEqual(expected, actual)
        self.assertFalse(self.error_output)
