{pkgs, ...}: {
  packages = with pkgs; [
    python313
  ];
  languages.python = {
    enable = true;
    package = pkgs.python314.withPackages (ps:
      with ps; [
        tkinter
        tox
      ]);
    venv.enable = true;
    uv = {
      enable = true;
      sync = {
        enable = true;
        allGroups = true;
      };
    };
  };
}
