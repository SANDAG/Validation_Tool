# Validation_Tool


## File structure:

- app.py: main script defining the layout of dash app. Including page layout design, scenario selector, menu and page switching and callbacks.
- Azure_load_data.py: script to read data from databricks
- Local_load_data.py: script to read data from T drive
- validation_plot_generator.py: includes a series functions about generating graphs, maps and layouts
- requirements.txt: required python packages (for both local and Azure web service)
- git workflow: automatically update changes into Azure web service and redeploy

  
## Deployment on Azure Web Service:

- set up environment variables (use token to read data from databricks)
  
` DATABRICKS_SERVER_HOSTNAME = https://adb-3893261652776219.19.azuredatabricks.net/ `

` DATABRICKS_HTTP_PATH = /sql/1.0/warehouses/41cbd7de44cc187c `

` DATABRICKS_TOKEN = your_token `
  
- set up start up command under configuration

![image](https://github.com/user-attachments/assets/ca3025c9-fb6e-4b84-bd95-124b1d0c60ff)

- Define the scenarios that you want to compare in Environment variables
  
![image](https://github.com/user-attachments/assets/83374ea8-bc83-4796-9a4c-fb959d249d0c)

Current Validation app:  https://validation-tool-hzhfg6cmgggndbh5.westus-01.azurewebsites.net/

## Deployment in Local environment:

- Makre sure you have access to T drive. Connect to VPN if needed

- Run `python app.py` and preview the dashboard in http://127.0.0.1:8050/

- Note that local version only have one scenario 1150

## Development Process

1. Clone Azure-dev in local
2. Edit script and review changes by running app locally:
   ` python app.py `
4. After checking, push changes to Azure-dev
5. It will automatically update in Azure web service by git workflow.
