{ pkgs }: {
  deps = [
    pkgs.chromium
    pkgs.xvfb-run
    # Dépendances NSS/NSPR
    pkgs.nss
    pkgs.nspr
    # Dépendances système
    pkgs.dbus
    pkgs.atk
    pkgs.at-spi2-atk
    pkgs.at-spi2-core
    pkgs.cups
    pkgs.libdrm
    pkgs.expat
    # Dépendances X11
    pkgs.xorg.libxcb
    pkgs.libxkbcommon
    pkgs.xorg.libXcomposite
    pkgs.xorg.libXdamage
    pkgs.xorg.libXfixes
    # Dépendances graphiques
    pkgs.mesa
    pkgs.pango
    pkgs.cairo
    # Dépendances audio
    pkgs.alsa-lib
  ];
} 