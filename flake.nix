{
  description = "pysmo dev shell";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = {
    self,
    nixpkgs,
  }: let
    forEachSystem = nixpkgs.lib.genAttrs [
      "x86_64-linux"
      "aarch64-linux"
      "x86_64-darwin"
      "aarch64-darwin"
    ];
  in {
    devShells = forEachSystem (
      system: let
        pkgs = nixpkgs.legacyPackages.${system};
      in {
        default = pkgs.mkShell {
          nativeBuildInputs = with pkgs; [
            gnumake
            autoPatchelfHook
            poetry
            python312
            python312Packages.tox
            python310
            python311
            python313
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
            # uncomment the next line to override default python version (i.e. the first one in nativeBuildInputs)
            # poetry env use -- 3.12
            poetry install

            # Tox might fail on the first run if the bins aren't already there...
            autoPatchelf .tox/lint/bin/
            source $VENV/bin/activate
          '';
        };
      }
    );
    formatter = forEachSystem (system: nixpkgs.legacyPackages.${system}.nixpkgs-fmt);
  };
}
