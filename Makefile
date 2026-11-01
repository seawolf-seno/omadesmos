# Build an Arch package from the repo: `make pkg`, then `sudo pacman -U omadesmos-*.pkg.tar.zst`
pkg:
	rm -rf build && mkdir build
	cp PKGBUILD omadesmos.py config.json data/* build/
	cd build && makepkg -fd && mv *.pkg.tar.zst ..

.PHONY: pkg
