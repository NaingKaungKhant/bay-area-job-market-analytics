"""Execute the two Phase 4 notebooks with real kernels in the current Python.

Uses temporary Jupyter paths; never installs a global kernel or changes user
settings. Notebook outputs are written only after successful execution.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

import nbformat
from nbclient import NotebookClient

from src.luke_dataset import digest_file

NOTEBOOKS=['notebooks/02_exploratory_analysis.ipynb','notebooks/03_descriptive_comparisons.ipynb']


def execute(root=Path('.')):
    root=Path(root).resolve()
    verification=root/'reports/phase4_verification.json'
    result=json.loads(verification.read_text()) if verification.exists() else {}
    entries=[]
    with tempfile.TemporaryDirectory(prefix='bay-phase4-jupyter-') as directory:
        temporary=Path(directory)
        kernel=temporary/'kernels/bay-area-phase4';kernel.mkdir(parents=True)
        (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
            'display_name':'Bay Area Phase 4 project Python','language':'python'}))
        changes={'JUPYTER_PATH':str(temporary)+(os.pathsep+os.environ['JUPYTER_PATH'] if os.environ.get('JUPYTER_PATH') else ''),
                 'JUPYTER_RUNTIME_DIR':str(temporary/'runtime'),
                 'MPLCONFIGDIR':str(temporary/'matplotlib'),
                 'XDG_CACHE_HOME':str(temporary/'cache'),
                 'IPYTHONDIR':str(temporary/'ipython'),
                 'JUPYTER_PLATFORM_DIRS':'1'}
        old={key:os.environ.get(key) for key in changes}
        os.environ.update(changes)
        try:
            for name in NOTEBOOKS:
                started=time.monotonic()
                notebook=nbformat.read(root/name,as_version=4)
                # Errors abort execution, rather than leaving an apparently successful notebook.
                client=NotebookClient(notebook,timeout=180,kernel_name='bay-area-phase4',
                    resources={'metadata':{'path':str(root)}})
                client.execute()
                code=[cell for cell in notebook.cells if cell.cell_type=='code' and cell.source.strip()]
                if any(cell.execution_count is None for cell in code):
                    raise ValueError('Notebook contains unexecuted code cells.')
                if any(output.output_type=='error' for cell in code for output in cell.get('outputs',[])):
                    raise ValueError('Notebook contains error outputs.')
                nbformat.write(notebook,root/name)
                entries.append({'notebook':name,'status':'executed','code_cells':len(code),'error_outputs':0,
                                'elapsed_seconds':round(time.monotonic()-started,3),'sha256':digest_file(root/name)})
                print(json.dumps(entries[-1]),flush=True)
        except Exception as exc:
            result.update(notebook_status='failed',notebooks=entries,notebook_error=type(exc).__name__+': '+str(exc))
            verification.write_text(json.dumps(result,indent=2)+'\n')
            raise
        finally:
            for key,value in old.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value
    result.pop('notebook_error',None)
    result.update(phase=4,verified_on=datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat(),
                  notebook_status='executed',notebooks=entries,kernel_python=sys.executable)
    verification.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':execute()
