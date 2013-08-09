all: ROS_NOBUILD

TARBALL_NAME = bt_cheetah
TARBALL = build/$(TARBALL_NAME).zip
TARBALL_URL = http://www.syntouchllc.com/Products/_software/$(TARBALL_NAME).zip
SOURCE_DIR = build/$(TARBALL_NAME)
UNPACK_CMD = unzip
include $(shell rospack find mk)/download_unpack_build.mk

ROS_NOBUILD: $(SOURCE_DIR)/unpacked
	mkdir -p lib
	cp $(SOURCE_DIR)/cheetah.so lib
	touch ROS_NOBUILD
	echo "created by rosmake to mark as installed" >> ROS_NOBUILD


clean:
	-rm -f ROS_NOBUILD
	-rm -rf lib

wipe: clean
	-rm -rf build
