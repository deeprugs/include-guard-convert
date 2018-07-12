
import shlex

regexes = {
                'ifndef' : '^\s*#(?:ifndef|IFNDEF)\s+([A-Za-z_0-9]{4,})\s*$',
                'ifndef2' : '^\s*(#(?:if !defined|IF !DEFINED)+\().*_H_.*\)\s*',
                'define' : '^\s*#(?:define|DEFINE)\s+([A-Za-z_0-9]{4,})\s*$',
                'endif' : '^\s*#(?:endif|ENDIF)\s*(/\*.*\*/|//.+)?\s*$',
                'blank' : '^\s*(/\*.*\*/|//.+)?\s*$',
                'pragma' : '^\s*#(?:pragma|PRAGMA)\s+(?:once|ONCE)'
}
patterns = dict( [ (key, re.compile(regexes[key]) ) for key in regexes.keys() ] )

cpp_commands = {
                'strip_comments' : 'cpp -w -dD -E -fpreprocessed  -P -x c++ {file}',
                'test_if_guarded' : 'cpp -w -P -x c++ -D{define} {file}'
}


class guarded_include(object):
        """
        Class representing an #include'able file (a.k.a. a header).
        """

        def __init__(self, filename, autoconvert = False):
                self.filename = filename
                assert(self._test_readable())
                if autoconvert and self.test_oldstyle_guarded():
                        self.convert()

        def _test_readable(self):
                return os.access(self.filename, os.R_OK)


        def test_oldstyle_guarded(self):
                try:
                        self._stripped = subprocess.check_output(
                                        shlex.split(
                                                        cpp_commands['strip_comments'].format(file=self.filename)
                                                        ),
                                        stderr=subprocess.STDOUT
                                        )
                        #print('\n*********************\n');
                        #print(self._stripped);
                        #print('\n*********************\n');

                        self._stripped = self._stripped.lstrip();
                        lineend = self._stripped.find('\n')
                        match_ifndef = patterns['ifndef'].search(self._stripped[:lineend])

                        #print('\n*********************\n');
                        print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n", lineend,'\n');
                        print("lineend =", lineend,'\n');
                        print(self._stripped[:lineend]);
                        #print('\n*********************\n');


                        global flag
                        flag='ifndef'
                        if not match_ifndef:
                                        match_ifndef = patterns['ifndef2'].search(self._stripped[:lineend])
                                        if match_ifndef is not None:
                                                flag='ifndef2'
                                                print('flag is ', flag)

                        if not match_ifndef:
                                        print(':-\ Did not match')
                                        return False


                        if (flag == 'ifndef'):
                                define = match_ifndef.group(1)
                                print("#ifdef is used. define is ",define)
                        else:
                                #str1.split("(")[1].split(")")[0]
                                define = self._stripped[:lineend].split("(")[1].split(")")[0]
                                print("#if !defined(...) is used. define is " + define)

                        print(cpp_commands['test_if_guarded'].format(file=self.filename, define=define))
                        with_define = subprocess.check_output(
                                        shlex.split(
                                                        cpp_commands['test_if_guarded'].format(file=self.filename, define=define)
                                                        ),
                                        stderr=subprocess.STDOUT
                                        )
                        if not len(with_define) < 2:
                                print("Some issue, please check \n")
                                return False

                        print("4\n");
                        fh = open(self.filename, 'r')
                        line = fh.readline()
                        print ("patterns[flag] is \n",patterns[flag] )
                        while not patterns[flag].search(line):
                                line = fh.readline()
                                if not len(line):
                                        fh.close()
                                        return False

                        line = fh.readline()
                        print("5\n");
                        fh.close()
                        return patterns['define'].search(line)

                except subprocess.CalledProcessError as err:
                        return False

        def convert(self):
                global flag
                freadh = open(self.filename, 'r')
                lines = freadh.readlines()
                sep = '\r\n' if lines[0].endswith('\r\n') else '\n'
                freadh.close()
                fwriteh = open(self.filename , 'w')
                for l_number in range(1,len(lines)):
                        line = lines[-l_number]
                        if patterns['blank'].search(line):
                                continue
                        elif patterns['endif'].search(line):
                                lines.pop(-l_number)
                                break
                        else:
                                raise SyntaxError('encountered meaningful line after last #endif: \n'+line)
                define = None
                done = False
                for l_number,line in enumerate(lines):
                        if done:
                                fwriteh.write(line)
                                continue
                        if define is None:
                                print("Flag is",flag);
                                if flag=='ifndef':
                                        pattern = patterns['ifndef']
                                else:
                                        print("Convert2");
                                        pattern = patterns['ifndef2']
                        else:
                                pattern = patterns['define']
                        match = pattern.search(line)
                        if match:
                                if flag=="ifndef":
                                        newdefine = match.group(1)
                                elif flag=="ifndef2":
                                        if define is None:
                                                print("PATTERN:", match.group(0))
                                                newdefine = match.group(0).split("(")[1].split(")")[0]
                                        else:
                                                newdefine =  match.group(0).split()[1]
                                                print("2nd line guard:", newdefine)

                                else:
                                        print("Error: Flag is", flag);

                                if define is None:
                                        define = newdefine
                                        print "define initialized to",define ;
                                elif define == newdefine:
                                        fwriteh.write('#pragma once' + sep)
                                        done = True
                        else:
                                fwriteh.write(line)
                if define is None:
                        raise SyntaxError('could not find #ifndef')
                elif define != newdefine:
                        raise SyntaxError('found #ifndef ' + define + ', does not match #define ' + newdefine)
                fwriteh.close()

if __name__ == '__main__':
        import argparse
        flag='ifndef'
        parser = argparse.ArgumentParser()
        parser.add_argument('filename', nargs='*')
        args = parser.parse_args()
        for filen in args.filename:
                try:
                        gi = guarded_include(filen)
                        if gi.test_oldstyle_guarded():
                                gi.convert()
                except SyntaxError as e:
                        print (filen)
                        print (e)
