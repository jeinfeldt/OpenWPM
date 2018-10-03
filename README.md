Measurement for Master Thesis
--------

I used this great open-source project as a basis for the research I did during my master thesis 
at the Media University in Stuttgart.
My contribution is the instrumentation of the crawler on top of OpenWPM (`crawl.py` and `crawler.py`) and the analysis script provided in the `measurement` folder.

The rest of the project was used as is at the time of forking. I performed crawls on top 100 to 100.000 sites and evaluated their behaviour regarding third-party online tracking.


Abstract of Thesis
--------
Online tracking is the practice of recording users’ browsing activities to infer in-
terests for personalised online advertising. Advertisements on the web are the
primary source of revenue and enable free content and services. An average user
pays for online services with his personal information in the form of his browsing
history. This data is not only available to the website a user visits, but also to other
unrelated third parties, embedded by the origin site. The main tool for this approach
is HTTP cookies. This practice poses a dilemma, as it is a prevalent business model
for publishers on the web, but also results in privacy and security concerns. The
reach of entities taking part in this practice and the potential of storage, disclosure,
and linkage of information is the core of online privacy concerns. 

This thesis aims to quantify approaches to online tracking by utilising the platform OpenWPM for
automated browsing and subsequent analysis of data. Different browser configu-
rations and localities are examined, with the result that US sites include twice as
many trackers as German sites. Privacy-preserving tools prove accountable for their
promises, with Ghostery reducing third-party cookies by 85% percent. Google and
Facebook are the most present third-party organisations with presence of roughly
90% and 50% of the top 500 Alexa sites in Germany. Moreover, logging in to Google
and Facebook before browsing the top 100 sites in Germany shows an increase in
third-party cookies of 78% and 92% respectively.

OpenWPM 
--------

OpenWPM is a web privacy measurement framework which makes it easy to collect
data for privacy studies on a scale of thousands to millions of site. OpenWPM
is built on top of Firefox, with automation provided by Selenium. It includes
several hooks for data collection, including a proxy, a Firefox extension, and
access to Flash cookies. Check out the instrumentation section below for more
details.




