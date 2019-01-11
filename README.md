
#DevSecOps -  Dome9 CI:CD Pipeline

The Dome9 CI/CD pipeline contain full pipeline for Continues Deployment and Continues Integration 

The Pipeline is based on AWS Code Pipeline Service 

It is Include two Dome9 core API usage - 
1. CFT static analysis using Dome9 static assessment execution 
2. Simulation of the given CFT and validation using Dome9 Compliance engine 
    1. Sync and wait script - That responsible to the dome9 fetch execution 
    2. Run assessment script that responsible to the run assessment execution and analysis of the simulated CFT
