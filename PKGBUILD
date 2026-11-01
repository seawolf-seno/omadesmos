# Maintainer: Steven Eno <seno@pacificachristian.org>
pkgname=omadesmos
pkgver=0.1.0
pkgrel=1
pkgdesc="Desmos calculators for Omarchy in a locked-down window (no general web browsing)"
arch=('any')
license=('MIT')
depends=('python' 'python-gobject' 'gtk3' 'webkit2gtk-4.1')
backup=('etc/omadesmos/config.json')
source=('omadesmos.py' 'config.json' 'org.pacificachristian.OmaDesmos.desktop' 'omadesmos.svg')
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
  install -Dm755 omadesmos.py "$pkgdir/usr/share/omadesmos/omadesmos.py"
  install -Dm644 config.json "$pkgdir/etc/omadesmos/config.json"
  install -Dm644 org.pacificachristian.OmaDesmos.desktop "$pkgdir/usr/share/applications/org.pacificachristian.OmaDesmos.desktop"
  install -Dm644 omadesmos.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/omadesmos.svg"
  install -dm755 "$pkgdir/usr/bin"
  ln -s /usr/share/omadesmos/omadesmos.py "$pkgdir/usr/bin/omadesmos"
}
