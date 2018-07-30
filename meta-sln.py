import sys
import glob
import time
import requests
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


def wait(url):
    # TODO: use the current git state here instead of the filesystem
    own_git_dir = get_root_dir(os.getcwd(), '.git')
    all_projects = glob.glob(os.path.join(get_root_dir(os.getcwd(), '.meta'), '**/*.csproj'), recursive=True)
    our_projects = glob.glob(os.path.join(own_git_dir, '**/*.csproj'), recursive=True)
    waiting_for = set()
    for our_project in our_projects:
        root = ET.parse(our_project)
        for item_group in root.findall('ItemGroup'):
            for project_reference in item_group.findall('ProjectReference'):
                abs_referenced_csproj_path = os.path.normpath(
                    os.path.join(
                        os.path.dirname(our_project),
                        project_reference.get('Include').replace('\\', '/')
                    )
                )
                referenced_git_dir = get_root_dir(os.path.dirname(abs_referenced_csproj_path), '.git')
                if own_git_dir != referenced_git_dir:
                    project_name = os.path.basename(abs_referenced_csproj_path[:-7])
                    project_version = get_git_version(referenced_git_dir)
                    waiting_for.add((project_name, project_version))
    for (project_name, project_version) in waiting_for:
        while True:
            print('Waiting for ' + str(project_name) + ' ' + str(project_version) + '...')
            request = requests.head(url + '/' + project_name.lower() + '/' + project_version + '.json')
            if request.status_code == 200:
                break
            time.sleep(10)


def touch():
    projects = glob.glob(os.path.join(get_root_dir(os.getcwd(), '.meta'), '**/*.csproj'), recursive=True)
    for project in projects:
        with open(project, 'r+') as f:
            # this runs on every commit and checkout, for two reasons:
            # (i)  update the modification time of all *.csproj to force `git status` to re-run the `clean` filter,
            #      allowing the version numbers to bump up. see: https://stackoverflow.com/a/41935511/810354
            # (ii) smudging the initial clone
            data = f.read()
            f.seek(0)
            f.write(smudge(project, data))
            f.truncate()
            f.close()


if __name__ == '__main__':
    try:
        get_root_dir(os.getcwd(), '.meta')
    except ValueError:
        sys.stdout.write(sys.stdin.read())
        exit(0)
    if len(sys.argv) == 2 and sys.argv[1] == 'touch':
        touch()
        exit(0)
    if len(sys.argv) != 3:
        print('Invalid arguments', file=sys.stderr)
        exit(1)
    if sys.argv[1] == 'clean':
        sys.stdout.write(clean(sys.argv[2], sys.stdin.read()))
    elif sys.argv[1] == 'smudge':
        sys.stdout.write(smudge(sys.argv[2], sys.stdin.read()))
    elif sys.argv[1] == 'wait':
        wait(sys.argv[2])
    else:
        print('Wat', file=sys.stderr)
        exit(1)
