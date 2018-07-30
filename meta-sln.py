import sys
import glob
import os.path
import subprocess
import xml.etree.ElementTree as ET


def get_root_dir(directory, look_for):
    abs_look_for = os.path.join(directory, look_for)
    if os.path.isfile(abs_look_for) or os.path.isdir(abs_look_for):
        return directory
    parent_directory = os.path.dirname(directory)
    if directory == parent_directory:
        raise ValueError()
    return get_root_dir(parent_directory, look_for)


def get_git_version(workingdir):
    p = subprocess.Popen(['gitversion', '-showvariable', 'NuGetVersionV2'], stdout=subprocess.PIPE, cwd=workingdir)
    return p.communicate()[0].decode('ascii').strip()


def clean(path, data):
    root = ET.fromstring(data)
    for item_group in root.findall('ItemGroup'):
        for project_reference in item_group.findall('ProjectReference'):
            own_git_dir = get_root_dir(os.getcwd(), '.git')
            abs_csproj_path = os.path.normpath(
                os.path.join(
                    own_git_dir,
                    path
                )
            )
            abs_referenced_csproj_path = os.path.normpath(
                os.path.join(
                    os.path.dirname(abs_csproj_path),
                    project_reference.get('Include').replace('\\', '/')
                )
            )
            referenced_git_dir = get_root_dir(os.path.dirname(abs_referenced_csproj_path), '.git')
            if own_git_dir != referenced_git_dir:
                project_reference.tag = "PackageReference"
                project_reference.set('Include', os.path.basename(abs_referenced_csproj_path[:-7]))
                project_reference.set('Version', get_git_version(referenced_git_dir))
    return ET.tostring(root).decode('utf8')


def smudge(path, data):
    projects = glob.glob(os.path.join(get_root_dir(os.getcwd(), '.meta'), '**/*.csproj'), recursive=True)
    root = ET.fromstring(data)
    for item_group in root.findall('ItemGroup'):
        for package_reference in item_group.findall('PackageReference'):
            matching_projects = [
                project for project in projects
                if os.path.basename(project[:-7]).lower() == package_reference.get('Include').lower()
            ]
            if any(matching_projects):
                matching_project = next(iter(matching_projects))
                relative_path = os.path.relpath(matching_project, os.path.dirname(path))
                package_reference.tag = "ProjectReference"
                package_reference.set('Include', relative_path)
                try:
                    del package_reference.attrib['Version']
                except KeyError:
                    pass
    return ET.tostring(root).decode('utf8')


if __name__ == '__main__':
    try:
        get_root_dir(os.getcwd(), '.meta')
    except ValueError:
        sys.stdout.write(sys.stdin.read())
        exit(0)
    if len(sys.argv) != 3:
        print('Invalid arguments', file=sys.stderr)
        exit(1)
    if sys.argv[1] == 'clean':
        sys.stdout.write(clean(sys.argv[2], sys.stdin.read()))
    elif sys.argv[1] == 'smudge':
        sys.stdout.write(smudge(sys.argv[2], sys.stdin.read()))
