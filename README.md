# Validation_Tool

## File structure:
- app.py: main script defining the layout of dash app. Including page layout design, scenario selector, menu and page switching and callbacks.
- load_data.py: script to read data from databricks
- validation_plot_generator: includes a series functions about generating graphs, maps and layouts
  
## Deployment on Azure Web Service:
- set up environment variables (use token to read data from databricks)
- set up start up command under configuration

![image](https://github.com/user-attachments/assets/ca3025c9-fb6e-4b84-bd95-124b1d0c60ff)

## Deployment in Local environment:
- set up .env file
  
> DATABRICKS_SERVER_HOSTNAME = https://adb-3893261652776219.19.azuredatabricks.net/
>
> DATABRICKS_HTTP_PATH = /sql/1.0/warehouses/41cbd7de44cc187c
> 
> DATABRICKS_TOKEN = your_token


Current Validation app:  https://validation-tool-hzhfg6cmgggndbh5.westus-01.azurewebsites.net/
