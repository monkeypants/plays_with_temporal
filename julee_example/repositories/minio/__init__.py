# This file intentionally left empty to avoid conflicts with the
# PyPI minio package.
#
# When pytest adds julee_example/repositories to sys.path, our local
# 'minio' directory can shadow the real 'minio' package from PyPI.
# By keeping this __init__.py empty, we ensure this directory is just
# a namespace container for our repository implementations, not a
# replacement for the real minio package.
#
# Import our implementations directly:
#   from julee_example.repositories.minio.document import \
#       MinioDocumentRepository
