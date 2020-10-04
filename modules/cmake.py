
DOCUMENTATION = '''
---
module: cmake
short_description: Manages CMake installations
description:
    - Manage I(cmake) installations from archives or directories
options:
    src:
        required: true
        description:
            - A directory containing the root CMakeLists.txt or an archive
              of a CMake project.
requirements:
    - cmake >= 2.8 
author: Jeff Caffrey-Hill (@ReverentEngineer)
'''


import os
import zipfile
import tarfile
from shutil import rmtree
from tempfile import mkdtemp
from ansible.module_utils.basic import AnsibleModule


def find_root_cmake(src_dir):
    ''' @brief Searches a source directory for a root CMakeLists.txt

    @param src_dir [in] The source directory

    @return The root source directory.
    '''
    return src_dir

def prepare_if_archive(src):
    ''' @brief Prepares source if its an archive. Otherwise, does noting.

    @param src [in] The CMake source code (archive or directory)
    
    @return The prepared source directory
    '''
    result = None
    if os.path.isdir(src):
        result = src
    elif os.path.isfile(src) and tarfile.is_tarfile(src):
        result = mkdtemp()
        with tarfile.open(src) as tar:
            tar.extractall(result)
    elif os.path.isfile(src) and zipfile.is_zipfile(src):
        result = mkdtemp()
        with zipfile.ZipFile(src) as zip:
            zip.extractall(result)
    return result 


def create_cmake_command(cmake_path, project_dir, install_dir, defines=None):
    """ @brief Create CMake command 

    @param cmake_path [in] Path to cmake
    @param project_dir [in] Path to CMake project root
    @param install_dir [in] Where to install CMake project
    @param defines [in] CMake variables to define

    @return CMake commmand
    """
    command = cmake_path
    command += " -DCMAKE_INSTALL_PREFIX=%s" % (install_dir)
    if defines:
        for define in defines:
            command += " -D%s=%s" % (define, defines[define])
    command += " %s" % project_dir
    return command


def main():
    module = AnsibleModule(
        argument_spec = dict(
            src         = dict(type='path', required=True),
            defines     = dict(type='dict'),
            install_dir = dict(type='str', required=True),
            cmake       = dict(type='path', default="cmake")
        )
    )
    
    src_dir = prepare_if_archive(module.params['src'])

    if not src_dir:
        module.fail_json(msg='Source is not a directory or known archive format')

    cmake_dir = find_root_cmake(src_dir)
    
    if not cmake_dir:
        module.fail_json(msg='Could not find CMake root directory')

    build_dir = mkdtemp()

    cmake_command = create_cmake_command(module.params['cmake'],
                                         cmake_dir,
                                         module.params['install_dir'],
                                         module.params['defines'])

    rc, out, err = module.run_command(cmake_command, check_rc=False, cwd=build_dir)

    if rc != 0:
        if src_dir != module.params['src']:
            rmtree(src_dir)
        rmtree(build_dir)
        module.fail_json(msg='Failed to generate build files, exit code %s' % (err))

    rc, out, err = module.run_command("make install", check_rc=False, cwd=build_dir)

    if rc != 0:
        if src_dir != module.params['src']:
            rmtree(src_dir)
        rmtree(build_dir)
        module.fail_json(msg='Failed to generate build files, exit code %s' % (err))

    if src_dir != module.params['src']:
        rmtree(src_dir)
    rmtree(build_dir)

    module.exit_json(changed=True, install_dir=module.params['install_dir'])

if __name__ == '__main__':
    main()
