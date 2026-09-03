import ee
import os
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.getenv('GEE_PROJECT_ID'))

tasks = ee.batch.Task.list()[:4]
for task in tasks:
    print(f"Task: {task.config['description']} | State: {task.state}")