{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.flask
    pkgs.python311Packages.flask_sqlalchemy
    pkgs.python311Packages.flask_login
    pkgs.python311Packages.setuptools
    pkgs.python311Packages.pip
  ];
}
