{
  description = "pysmo dev shell";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    ...
  } @ inputs:
    flake-utils.lib.eachDefaultSystem (
      system: let
        pkgs = import nixpkgs {
          inherit system;
        };
      in {
        devShells = {
          default = pkgs.mkShell {
            nativeBuildInputs = with pkgs; [
              gnumake
              autoPatchelfHook
              poetry
              python312
              python313Full
              python313Packages.tox
            ];

            shellHook = ''
              export LD_LIBRARY_PATH=${with pkgs;
                lib.makeLibraryPath [
                  stdenv.cc.cc.lib
                  zlib
                ]}:$LD_LIBRARY_PATH
              VENV=.venv
              export POETRY_ACTIVE="true"
              export POETRY_VIRTUALENVS_IN_PROJECT="true"
              export POETRY_VIRTUALENVS_PATH=$VENV
              poetry env use -- 3.13
              poetry install

              # Tox might fail on the first run if the bins aren't already there...
              autoPatchelf .tox/lint/bin/
              source $VENV/bin/activate
            '';
          };
        };
        formatter = pkgs.nixpkgs-fmt;
      }
    );
}
