# SANDAG Validation Tool

<br>

The SANDAG Validation Tool is a Python-Dash web application designed to validate travel model outputs against observed traffic and transit counts. It allows transportation planners and analysts to visualize model performance across multiple scenarios with interactive plots, statistics, and geospatial maps. The app is deployed both locally and on Azure using automated GitHub Actions workflows.

🔗 Live App: [validation-tool](https://validation-tool-hzhfg6cmgggndbh5.westus-01.azurewebsites.net/)

📦 Tech Stack: Python · [Dash](https://dash.plotly.com/) · [Plotly](https://plotly.com/) · [Dash Leaflet](https://www.dash-leaflet.com/) · Azure Web App · Databricks · GitHub Actions

<br>
  
## ✨ Features:

**Scenario Comparison**: Select and compare model scenarios for different time periods and vehicle classes.

**Volume & VMT Validation**: Compare modeled vs. observed flows and VMT by geography, volume category, and road class.

**Truck Validation**: Analyze light/heavy/mid-duty trucks with year-based filters.

**Transit Validation**: Evaluate model performance for transit boardings across modes and TODs.

**Interactive Maps**: Visualize segment-level or route-level performance gaps on styled Leaflet maps.

**Automated CI/CD**: Changes pushed to dev or main trigger deployment to Azure dev or production slots respectively.

<br>

## 📁 File structure:
```
.
├── .github
│   └── workflows
│       └── azure_dev_validation-tool.yml
|       └──main_validation-tool.yml
├── .gitignore
├── README.md
├── app.py
├── config.yaml
├── load_data.py
├── requirements.txt
└── validation_plot_generator.py
```

- app.py: main script defining the layout of dash app. Including page layout design, scenario selector, menu and page switching and callbacks.
- load_data.py: script to read data from databricks and T drive according to environment
- validation_plot_generator.py: includes a series functions about generating graphs, maps and layouts
- requirements.txt: required python packages (for both local and Azure web service)
- config.yaml: config file for local use. Set up scenarios that will load in app.
- git workflow: automatically update changes into Azure web service and redeploy (main branch to production slot and dev branch to dev slot)

<br>

## 🛠️ Data Pipeline

![image](https://github.com/user-attachments/assets/25da37da-33a4-448d-ac24-2248eb8ca4ae)

<br>

## 🔁 Development Process

1. Clone repo in local
2. In dev branch, edit script and review changes by running app locally:
   ` python app.py `
4. After checking, push changes to original dev branch
5. It will automatically update dash app in dev slot in Azure web service by git workflow. Test updates by reviewing site.
6. After testing, merge change from dev branch to main branch. And this updates in main branch will trigger workflow to update dash app in production slot in Azure web service.
![image](https://github.com/user-attachments/assets/961f1746-3cb0-4f21-8990-4b6d7be91184)

<br>

## ⚙️Local Setup:

1.  Makre sure you have access to T drive. Connect to VPN if needed
2.  Create a virtual environment and install packages in `requirements.txt`

3.  Set up scenarios that you want to load in app by `config.yaml`
  
     `LOCAL_FLAG:1`
     
     `LOCAL_SCENARIO_LIST:
        - T:\***`
    
   Define LOCAL_SCNEARIO_LIST as data paths of all scenarios that you want to compare in the visualization board
    
5.  Launch app: Run `python app.py` in terminal and preview the dashboard in http://127.0.0.1:8050/
   
6.  Press ctrcl c to stop

<br>

## ☁️ Azure Deployment:

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


