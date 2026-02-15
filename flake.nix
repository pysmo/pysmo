{
  description = "pysmo dev shell";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    systems.url = "github:nix-systems/default";
  };

  outputs = {
    self,
    nixpkgs,
    systems,
    ...
  }: let
    eachSystem = nixpkgs.lib.genAttrs (import systems);
  in {
    devShells = eachSystem (system: let
      pkgs = import nixpkgs {
        inherit system;
      };
    in {
      default = pkgs.mkShell {
        nativeBuildInputs = with pkgs; [
          gnumake
          uv
          ruff
          (python314.withPackages (ps: with ps; [tkinter]))
          (python313.withPackages (ps: with ps; [tox]))
          python312
          python314Packages.tkinter
        ];

        shellHook = ''
          export LD_LIBRARY_PATH=${with pkgs;
            lib.makeLibraryPath [
              stdenv.cc.cc.lib
              zlib
              libX11
            ]}:$LD_LIBRARY_PATH
          export MPLBACKEND="TKAgg"
          export PYSMO_SAVE_FIGS=true
          export UV_PYTHON=$(which python3.14)
          export UV_NO_MANAGED_PYTHON=true
          [ ! -d .venv ] && uv venv --system-site-packages
          uv sync --locked --all-extras
        '';
      };
    });
    formatter = eachSystem (system: (import nixpkgs {inherit system;}).nixpkgs-fmt);
  };
}
