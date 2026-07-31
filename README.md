# OpendTect-Apps
Miscellaneous stand-a-lone applications/tools for working with OpendTect projects and data. The applications also serve as demonstrations of the OpendTect ODBind Python bindings.

## Table of Contents (Optional)
- [Tools](#tools)
- [Installation](#usage)
- [License](#license)
- [Contributing](#contributing)

## Tools
- **zipmodel_runner**: apply ZipModels to OpendTect data

## Installation
Install the **pixi** package manager, see instructions [here](https://pixi.prefix.dev/latest/installation/)

Clone the repository.
```bash
cd 
git clone 
```
Edit **pixi.toml** and change the **ODPYTHON**  variable in the **[activation.env]** section to point to your OpendTect installation. Use the **pixi run** command to start an application
```bash
pixi run zipmodel
```

## License
[GNU GPLv3.0](https://github.com/waynegm/OpendTect-Apps/blob/main/LICENSE)

## Contributing
