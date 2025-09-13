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
              uv
              ruff
              python312
              python313
              python313Packages.tox
              python313Packages.tkinter
            ];

            shellHook = ''
              export LD_LIBRARY_PATH=${with pkgs;
                lib.makeLibraryPath [
                  stdenv.cc.cc.lib
                  zlib
                  xorg.libX11
                ]}:$LD_LIBRARY_PATH
              [ ! -d .venv ] && uv venv --system-site-packages --no-managed-python
              uv sync --locked --all-extras
              export MPLBACKEND="TKAgg"
              export PYSMO_SAVE_FIGS=true
            '';
          };
        };
        formatter = pkgs.nixpkgs-fmt;
      }
    );
}
