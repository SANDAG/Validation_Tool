# Validation_Tool


## File structure:
```
.
├── .github
│   └── workflows
│       └── azure_dev_validation-tool.yml
├── .gitignore
├── README.md
├── app.py
├── load_data.py
├── requirements.txt
└── validation_plot_generator.py
```

- app.py: main script defining the layout of dash app. Including page layout design, scenario selector, menu and page switching and callbacks.
- load_data.py: script to read data from databricks and T drive according to environment
- validation_plot_generator.py: includes a series functions about generating graphs, maps and layouts
- requirements.txt: required python packages (for both local and Azure web service)
- git workflow: automatically update changes into Azure web service and redeploy


## Deployment in Local environment:

1.  Makre sure you have access to T drive. Connect to VPN if needed
2.  Create a virtual environment and install packages in `requirements.txt`

3.  Create local yam file `config.yaml`
  
     `LOCAL_FLAG:1` **(required!)**
     
     `LOCAL_SCENARIO_LIST:
        - T:\***`
    
     Then define LOCAL_SCNEARIO_LIST as data paths of all scenarios that you want to compare in the visualization board

4.  Run `python app.py` in terminal and preview the dashboard in http://127.0.0.1:8050/
   
5.  Press ctrcl c to stop

## Deployment on Azure Web Service:

- set up environment variables (use token to read data from databricks)
  
  ` DATABRICKS_SERVER_HOSTNAME = ***`
  
  ` DATABRICKS_HTTP_PATH = ***`
  
  ` DATABRICKS_TOKEN = your_token `
  
  `SCM_DO_BUILD_DURING_DEPLOYMENT=true` **(required!)**
  
- set up start up command under configuration

  `gunicorn --workers 4 app:server`
  
  ![image](https://github.com/user-attachments/assets/ca3025c9-fb6e-4b84-bd95-124b1d0c60ff)

- Define the scenarios that you want to compare in Environment variables
  
   `AZURE_SCENARIO_LIST=1150,272,254`
   
   ![image](https://github.com/user-attachments/assets/69bef241-b150-46df-87f5-cc35b14bf139)

Current Validation app:  https://validation-tool-hzhfg6cmgggndbh5.westus-01.azurewebsites.net/


## Development Process

1. Clone main branch in local
2. Edit script and review changes by running app locally:
   ` python app.py `
4. After checking, push changes to dev branch
5. It will automatically update dash app in dev slot in Azure web service by git workflow. Test updates by preview of dev slot.
6. After testing, merge change from dev branch to main branch. And this updates in main branch will trigger workflow to update dash app in production slot in Azure web service.
