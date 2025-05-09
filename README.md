# Validation_Tool

- Test Locally
1. Set up a seperate environment according to local_environment.yaml
2. Make sure you can access T drive (connect to VPN if needed)
3. Clone the repo in the location you want
4. Open terminal and input command'python app.py'
5. Wait for page loading and then click the link in the ouput
eg: 'Dash is running on http://127.0.0.1:8050/'
6. To close app, kill or end terminal


- Test on Databricks
1. Create a git folder. And Clone from this repo
2. Create a app in Databricks. After starting the compute, deploy from the git folder you just created.
3. Make sure you have access to compute resource and data stored in catelog. Otherwise app will crash.
4. Remember **STOP** app when you are not using it. It cost money running apps in databricks!

Current Validation app: https://adb-3893261652776219.19.azuredatabricks.net/apps/validation?o=3893261652776219

