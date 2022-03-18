import subprocess

if __name__ == '__main__':

    p = subprocess.run(['icat.exe', '\\\\.\\C:', '6', '>',
                        'C:\\Users\\celin\\UNIVERSITÉ\\MA2S2\\Travail de Master\\Forensic-Tools\\data\\$bitmap'],
                       cwd='.\\sleuthkit\\bin\\', shell=True)
