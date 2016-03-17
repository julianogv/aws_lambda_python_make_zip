from boto3 import Session
from distutils.sysconfig import get_python_lib
import os
import shutil
import tempfile
import zipfile

__author__ = 'juliano'


def list_files(path, ignore_hidden=True):
    ignore_list = ["__pycache__", "setuptools", "pip", "pip-1.5.6.dist-info", "tests", "mock"]
    ret = []
    for item in os.listdir(path):
        if ignore_hidden and item.startswith("."):
            continue
        if item in ignore_list:
            continue
        item = os.path.join(path, item)
        if os.path.isdir(item):
            ret.extend(list_files(item))
        else:
            ret.append(item)
    return ret


def zip_dir(path, dst_zip_path):
    zipf = zipfile.ZipFile(dst_zip_path, 'w')
    for root, dirs, files in os.walk(path):
        for file in files:
            fp = os.path.join(root, file)
            # ignore hidden folders/files
            if not os.path.isfile(fp):
                continue
            arc = os.path.join(root.replace(path, ''),
                               os.path.basename(file))
            zipf.write(fp, arcname=arc)
    zipf.close()


def copy_files(src, dst):
    file_list = list_files(src)
    for file_ in file_list:
        relative_file_path = file_[len(src)+1:]
        dst_file_path = os.path.join(dst, relative_file_path)
        if not os.path.exists(os.path.dirname(dst_file_path)):
            os.makedirs(os.path.dirname(dst_file_path))
        print("%s > %s" % (file_, dst_file_path))
        shutil.copy(file_, dst_file_path)


if __name__ == "__main__":
    lambda_function_name = 'LAMBDA_FUNCTION_NAME'
    s3_bucket_name = "S3_BUCKET_NAME"
    aws_access_key = "AWS_ACCESS_KEY"
    aws_secret_access_key = "AWS_SECRET_ACCESS_KEY"
    region_name = "AWS_REGION_NAME"

    # YOUR CODE ROOT DIR
    code_path = os.path.dirname(os.path.abspath(__file__))

    # YOUR SITE PACKAGES ROOT DIR
    site_packages_dir = get_python_lib()

    aws_session = Session(aws_access_key_id=aws_access_key,
                          aws_secret_access_key=aws_secret_access_key,
                          region_name=region_name)

    tmp_dir = tempfile.mkdtemp()
    dst_zip_path = os.path.join(tempfile.gettempdir(), "%s.zip" % lambda_function_name)

    print("[x] Using:\n\t- %s\n\t- %s" % (code_path, site_packages_dir))

    try:
        copy_files(src=code_path, dst=tmp_dir)
        copy_files(src=site_packages_dir, dst=tmp_dir)

        if os.path.exists(dst_zip_path):
            os.remove(dst_zip_path)
        zip_dir(tmp_dir, dst_zip_path)
    finally:
        shutil.rmtree(tmp_dir)

    print("[x] Sending zip to s3...")
    s3 = aws_session.resource('s3')
    s3_file_name = '%s.zip' % lambda_function_name
    s3.Bucket(s3_bucket_name).put_object(Key=s3_file_name, Body=open(dst_zip_path, 'rb'))

    print("[x] Updating lambda code...")
    lambda_ = aws_session.client('lambda')
    lambda_.update_function_code(FunctionName=lambda_function_name,
                                 S3Bucket=s3_bucket_name,
                                 S3Key=s3_file_name,
                                 Publish=True)
    print("[x] Done")
