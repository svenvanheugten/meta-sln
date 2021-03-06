meta-sln
========

This is a proof-of-concept that allows you to work with multiple solutions spread over multiple repositories, as if the projects were all in one single mono-solution.

The only way this depends on [meta](https://github.com/mateodelnorte/meta) is that it stops searching for dependencies in the directory containining the `.meta` folder, so it can easily be adapted to work without meta-repo's.

It's also worth noting that the current implementation is completely incomprehensible. To be fixed.

What on earth is this thing?
----------------------------
Consider the [meta](https://github.com/mateodelnorte/meta)-repo [meta-sln-test](https://github.com/svenvanheugten/meta-sln-test), which consists of two projects, each in their own solution, each in their own repository:

- [meta-sln-test-interfaces/Interfaces](https://github.com/svenvanheugten/meta-sln-test-interfaces/blob/master/Interfaces/Interfaces.csproj)

```xml
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>netstandard2.0</TargetFramework>
  </PropertyGroup>

</Project>
```

- [meta-sln-test-implementation/Implementation](https://github.com/svenvanheugten/meta-sln-test-implementation/blob/master/Implementation/Implementation.csproj)

```xml
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>netstandard2.0</TargetFramework>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Interfaces" Version="0.1.0" />
  </ItemGroup>

</Project>
```

Clone the [meta](https://github.com/mateodelnorte/meta)-repo [meta-sln-test](https://github.com/svenvanheugten/meta-sln-test) like this:

```bash
meta git clone https://github.com/svenvanheugten/meta-sln-test
meta git checkout .  # fix unmodified csproj files showing up as modified just after the initial clone
```

You will find that your local copy of `Implementation.csproj` looks like this:

```xml
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>netstandard2.0</TargetFramework>
  </PropertyGroup>

  <ItemGroup>
    <ProjectReference Include="..\..\interfaces\Interfaces\Interfaces.csproj" />
  </ItemGroup>

</Project>
```

However, when you commit it, it is still a `PackageReference` with a version number, which is bumped up automatically whenever the `Interfaces`-project changes.

When you finally go ahead and `meta git push` everything, we need to make sure the new `Interfaces`-package is built and pushed _before_ the `Implementation`-package. The `git push`-commands run in the order of the `.meta` file, and the pre-push hook waits for the dependencies of every project to become available on the NuGet server before pushing the dependent project, simulating the phased deploy you would normally do yourselves.


Installation
------------
Add to `~/.gitconfig`:

```ini
[filter "meta-sln"]
    clean = python ~/meta-sln/meta-sln.py clean %f
    smudge = python ~/meta-sln/meta-sln.py smudge %f
    required
```

Add to `~/.config/attributes`:

```
*.csproj filter=meta-sln
```

Create `~/.config/git/hooks/pre-push`:

```bash
#!/bin/bash

python ~/meta-sln/meta-sln.py wait https://api.nuget.org/v3/registration3
```

Create `~/.config/git/hooks/post-commit`:

```bash
#!/bin/bash

python ~/meta-sln/meta-sln.py touch
```

Create `~/.config/git/hooks/post-checkout`:

```bash
#!/bin/bash

python ~/meta-sln/meta-sln.py touch
```

Now run `git config --global core.hooksPath ~/.config/git/hooks`.
