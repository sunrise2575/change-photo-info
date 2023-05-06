import PIL.Image
import argparse
import datetime
import dateutil.parser
import os
import piexif
import typing


def split_path(filepath: str) -> typing.Tuple[str, str, str]:
    dir, basename = os.path.split(filepath)
    name, ext = os.path.splitext(basename)
    return dir, name, ext


def dd_to_dms(latitude: float, longitude: float) -> typing.Dict[str, typing.Any]:
    def deg_to_dms(deg: float) -> typing.Tuple[typing.Tuple[int, int], typing.Tuple[int, int], typing.Tuple[int, int]]:
        d = int(deg)
        md = abs(deg - d) * 60
        m = int(md)
        sd = (md - m) * 60
        return ((d, 1), (m, 1), (int(sd*10000), 10000))

    if (-90.0 < latitude or latitude < 90.0) or \
            (-180.0 < longitude or longitude < 180.0):
        raise IndexError

    return {
        'GPSLatitudeRef': b'N' if latitude > 0 else b'S',
        'GPSLatitude': deg_to_dms(latitude),
        'GPSLongitudeRef': b'E' if longitude > 0 else b'W',
        'GPSLongitude': deg_to_dms(longitude),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", dest="folder",
                        action="store", required=True)
    parser.add_argument("-n", "--notime", dest="modify_timestamp",
                        action="store_false", default=True, required=False)
    parser.add_argument("-g", "--gps", dest="gps_dd",
                        action="store", default=None, required=False)
    args = parser.parse_args()

    my_folder = args.folder

    modify_timestamp = args.modify_timestamp

    latitude, longitude = None, None

    if args.gps_dd is not None:
        temp = str(args.gps_dd).split(',')
        latitude, longitude = float(temp[0]), float(temp[1])

    for filepath in os.listdir(my_folder):
        filepath = os.path.abspath(os.path.join(my_folder, filepath))
        if not os.path.isfile(filepath):
            continue

        _, name, ext = split_path(filepath)
        #timestamp = datetime.datetime.strptime(name, '%Y%m%d_%H%M%S')
        timestamp = dateutil.parser.parse(name, fuzzy=True)

        img = PIL.Image.open(filepath)
        img.verify()

        # after verify(), must reopen
        img = PIL.Image.open(filepath)
        if img._getexif() is None:
            # set a new empty EXIF data
            exif_dict = {'0th': {}, '1st': {}, 'Exif': {},
                         'GPS': {}, 'Interop': {}, 'thumbnail': None}
        else:
            exif_dict = piexif.load(img.info['exif'])

        if modify_timestamp:
            time_str = bytes(timestamp.strftime('%Y:%m:%d %H:%M:%S'), 'utf-8')
            exif_dict['0th'][piexif.ImageIFD.DateTime] = time_str
            exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = time_str
            exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = time_str

        if (latitude is not None) and (longitude is not None):
            dms = dd_to_dms(latitude, longitude)
            exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = dms['GPSLatitudeRef']
            exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = dms['Latitude']
            exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = dms['LongitudeRef']
            exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = dms['Longitude']
            exif_dict['GPS'][piexif.GPSIFD.GPSAltitudeRef] = 0
            exif_dict['GPS'][piexif.GPSIFD.GPSAltitude] = (0, 1000)
            if modify_timestamp:
                exif_dict['GPS'][piexif.GPSIFD.GPSDateStamp] = bytes(
                    timestamp.strftime('%Y:%m:%d'), 'utf-8')

        # save
        exif_raw = piexif.dump(exif_dict)

        if ext == '.png':
            img.save(filepath, format="PNG", exif=exif_raw)
        if ext == '.jpg':
            img.save(filepath, format="JPEG", exif=exif_raw)


if __name__ == '__main__':
    main()
