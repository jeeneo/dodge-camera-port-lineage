## This guide is a WIP

**Full credit to the [dodge-camera-port](https://github.com/dodge-camera-port) team and LineageOS maintainers for this device, I am not doing anything besides just putting peices together that somehow work.**

Building LineageOS w/ OnePlus Camera for dodge (CPH2655)

<details>
<summary>additional info</summary>
This guide assumes you know midrange knowledge on Linux and the Android build system (not really for beginners) and have a decent PC to build on. I have 32gb ram+swap w/ Ryzen 9 270 and on an NVME, a cold-build takes me ~3 hours, but successive builds are much faster. You'll need about ~360gb of free space and decent internet bandwith.

I won't be explaining how to set up a built environment past the usual `repo sync` LineageOS baseline and adding the Camera on top.
You can follow [Lineage's build guide](https://wiki.lineageos.org/devices/dodge/build) to do everything leading up to it.

This is meant to be a guide for me to understand the flow on how to patch Lineage's trees with the camera to keep the changes minimal to apply additional fixes from [upstream](https://github.com/dodge-camera-port) and to Lineage. I am not an expert by any means, it's been a while since I've done this.
</details>

Please read this guide all the way through before acting on it.

----
For NixOS:

I use a modified `shell.nix` to setup a FHS compatible shell.

Inside wherever you put the `shell.nix` in this repo:

```sh
nix-shell --pure && cd <lineage root>
```

ccache is placed inside `/tmp/ccache`, you can delete this if not needed, or disable ccache completely.

----

### Preparing device trees:

NOTE: If you already have the Lineage repos, you will need to reset/patch your repo accordingly to the approperate device trees. This guide assumes it's a fresh start.

`cd android/lineage` (or wherever you want to download the repos)

Verify git-lfs is initilized:
```sh
git lfs install
```

<!-- repo init -u https://github.com/LineageOS/android.git -b lineage-23.2 --git-lfs --no-clone-bundle -g all,-notdefault,+pdk,-darwin,-platform-darwin -->

```sh
repo init -u https://github.com/LineageOS/android.git -b lineage-23.2 --git-lfs --no-clone-bundle
```

Create the source tree manifest: `.repo/local_manifests/roomservice.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<manifest>
  <remote name="dodge-camera-port" fetch="https://github.com/dodge-camera-port/" />

  <project path="device/oneplus/dodge" name="android_device_oneplus_dodge" remote="dodge-camera-port" revision="16.0" />
  <project path="device/oneplus/sm8750-common" name="LineageOS/android_device_oneplus_sm8750-common" remote="github" revision="lineage-23.2" />
  <project path="device/qcom/sepolicy_vndr" name="android_device_qcom_sepolicy_vndr" remote="dodge-camera-port" revision="lineage-23.2-caf-sm8750" />
  
  <project path="hardware/oplus" name="android_hardware_oplus" remote="dodge-camera-port" revision="16.0" />
  
  <project path="vendor/oneplus/dodge" name="proprietary_vendor_oneplus_dodge" remote="dodge-camera-port" revision="lineage-23.2" />
  <project path="vendor/oneplus/sm8750-common" name="proprietary_vendor_oneplus_sm8750-common" remote="dodge-camera-port" revision="lineage-23.2" />
  <project path="vendor/oplus/camera" name="vendor_oplus_camera" remote="dodge-camera-port" revision="A16" />
  
  <project path="kernel/oneplus/sm8750" remote="github" name="LineageOS/android_kernel_oneplus_sm8750" />
  <project path="kernel/oneplus/sm8750-devicetrees" remote="github" name="LineageOS/android_kernel_oneplus_sm8750-devicetrees" />
  <project path="kernel/oneplus/sm8750-modules" remote="github" name="LineageOS/android_kernel_oneplus_sm8750-modules" />
  
</manifest>
```

Then run `repo sync` and take a break, check back in about an hour or two depending on your internet.

Once the repo has finshed syncing, proceed to next step.

### Preparing camera tree

Download `RegionalHybrid Flasher 13 GLO 16.0.8.301.zip` from [here](https://sourceforge.net/projects/oneplus13flashers/files/Oneplus%2013/Regional%20Flashers/Global/RegionalHybrid%20Flasher%2013%20GLO%2016.0.8.301.zip/download), you'll need to extract files from certain partitions in the next step.

You will need `fsck.erofs`, install this using your distros package manager, usually in `erofs-utils`

Once the above zip has been downloaded and extracted, open a terminal then run the whole command inside `OOS_FILES_HERE`:

```shell
mkdir -p extracted
for name in my_product my_stock system_ext odm system vendor; do
  rm -rf "extracted/$name" && mkdir -p "extracted/$name"
  fsck.erofs --extract="extracted/$name" "$name.img"
  echo "extracting $name"
done
echo "extracted files: \"$(pwd)/extracted\""
```

Copy the path following, `extracted files:` including the quotes, you will need this below:

Open a terminal to `vendor/oplus/camera`, run `./extract-files.py --allow-prohibited-files <path>`

Then, in `vendor/oplus/camera/camera/Android.bp`, modify the area containing `libcsextimpl` before the end brackets:

```
    system_ext_specific: true,
    allow_undefined_symbols: true, // add this line
```

### Patching

We have to patch some lineage/camera trees to succeed building.

Navigate back to repos root: `cd ../../../`

Inside `build/soong/scripts/check_boot_jars/package_allowed_list.txt`

Find `# OPLUS adds` and insert:

```
# OPLUS adds
com\.oplus\..*
oplus\..* # add
com\.color\..* # add
net\.oneplus\..* # add
vendor\.oplus\..* # add
```

In `device/oneplus/dodge/device.mk`, remove/comment out:

```makefile
PRODUCT_PACKAGES += \
    OplusLtpo
```

In `device/oneplus/dodge/lineage_dodge.mk`, remove/comment out:

```makefile
$(call inherit-product, vendor/gapps/arm64/arm64-vendor.mk)
```

In: `device/oneplus/sm8750-common/BoardConfigCommon.mk`, look for `SEPolicy`, add:

```
# SEPolicy
include device/lineage/sepolicy/qcom/sepolicy.mk # add this line above
include device/qcom/sepolicy_vndr/SEPolicy.mk
include hardware/oplus/sepolicy/qti/SEPolicy.mk
```

In: `device/qcom/sepolicy_vndr/sm8750/generic/vendor/common/domain.te`

Look for line ~73 `neverallow { domain`, the block should look like this:

```
neverallow { domain
- init
- vendor_init
- ueventd
- shell
- vendor_adsprpcd
- vendor_cdsprpcd
- vendor_sensors
- vendor_lowirpcd_service
- vendor_audioadsprpcd
- vendor_chre
- vendor_dspservice
- vendor_vppservice
- vendor_hexlpservice
- hal_contexthub_default
- hal_sensors_default
- hal_camera_default
- hal_audio_default
- opluscamera_app # add this line
userdebug_or_eng(` -vendor_usta_app')
userdebug_or_eng(` -vendor_ustaservice_app')
userdebug_or_eng(` -vendor_sysmonapp_app_test')
userdebug_or_eng(` -vendor_snapcam_app')
}vendor_xdsp_device:chr_file *;

neverallow { domain -init -vendor_init - ueventd -opluscamera_app } vendor_xdsp_device:chr_file ~{r_file_perms}; # adds `-opluscamera_app` after ueventd
```

In: `device/qcom/sepolicy_vndr/sm8750/generic/vendor/common/hal_camera.te` around line 91: `# Offline camera service access`:

replace:

```
# Offline camera service access
hal_attribute_service(hal_camera, vendor_hal_offlinecamera_service)
```

with:

```
# Offline camera service access
add_service(hal_camera_server, vendor_hal_offlinecamera_service)
neverallow { domain -hal_camera_server } vendor_hal_offlinecamera_service:service_manager add;
neverallow { domain -hal_camera_client -hal_camera_server -opluscamera_app -traceur_app -atrace -shell -system_app } vendor_hal_offlinecamera_service:service_manager find;
```

The following patches are automatic cherry-picking of upstreams fixes for Android's framework:

```sh
cd frameworks/av
git checkout -b camera-port-patches

git fetch https://github.com/dodge-camera-port/android_frameworks_av-common.git avium-16.2
git fetch https://github.com/dodge-camera-port/android_frameworks_av 16.0

git cherry-pick -X theirs b49833c569
git cherry-pick -X theirs 1f8a9704d7
git cherry-pick -X theirs 2e6e847dde
```

In `services/camera/libcameraservice/Android.bp`, remove this block:

```
    whole_static_libs: select(soong_config_variable("libcameraservice", "ext_lib"), {
        any @ flag_val: [flag_val],
        default: ["libcameraservice_ext_lib"],
    }),
```

Then commit `git add services/camera/libcameraservice/Android.bp && git commit -m "Fixup"` and continue with picking:

```sh
git cherry-pick -X theirs 39e7783a4b
git cherry-pick -X theirs d6654b364c
git cherry-pick -X theirs a985608795
git cherry-pick -X theirs 9f67b2e87e
git cherry-pick -X theirs 1af7f38878
git cherry-pick -X theirs b362ac249c
git cherry-pick -X theirs 45b355f49e
```

Then:

```sh
cd ../native
git checkout -b camera-port-patches

git fetch https://github.com/dodge-camera-port/android_frameworks_native.git 16.0
git cherry-pick -X theirs 22a9fd3607
cd ..
```

In `av/services/camera/libcameraservice/common/CameraProviderManager.cpp`:

Remove the line `#include "common/CameraProviderExtension.h"`

And in `base/Android.bp` look for the line `name: "framework-minus-apex-headers"` after `"//packages/modules/Virtualization:__subpackages__",`, add:

```
"//hardware/oplus/oplus-fwk",
```

After this is done, you should be good to build:

```sh
# back to lineage root
cd ..

source build/envsetup.sh
croot
breakfast dodge
brunch dodge
```

If successful, the built rom will be inside `out/target/product/dodge`.
