import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['KERNEL_DB_PATH']=str(Path(tempfile.mkdtemp())/'kernel-test.sqlite3')
from alembic.config import Config
from alembic import command
command.upgrade(Config(str(Path(__file__).resolve().parents[1]/'alembic.ini')),'head')
