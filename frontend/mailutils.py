#encoding: utf-8

import urllib
from smtplib import SMTP
from smtplib import SMTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
 
#Global varialbes
EMAIL_SUBJECT = "Email from Python script"
EMAIL_RECEIVERS = ['pablobesada@gmail.com', 
#, 'santiagoappiani@gmail.com', 'fedegisbert@gmail.com'
]
EMAIL_SENDER  =  'nuev9info@gmail.com'
EMAIL_PASSWORD = 'monitor678'
GMAIL_SMTP = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587
TEXT_SUBTYPE = "plain"
 
def listToStr(lst):
    """This method makes comma separated list item string"""
    return ','.join(lst)
 
def send_email(receivers, subject, content_text, content_html=None):
    """This method sends an email"""    
     
    #Create the message
    if content_html:
        msg = MIMEMultipart('alternative')
        msg.set_charset("utf-8")        
        part1 = MIMEText(content_text, 'plain', "utf-8")
        part2 = MIMEText(content_html, 'html', "utf-8")
        msg.attach(part1)
        msg.attach(part2)        
    else:
        msg = MIMEText(content_text, TEXT_SUBTYPE, "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = listToStr(receivers)
     
    try:
      smtpObj = SMTP(GMAIL_SMTP, GMAIL_SMTP_PORT)
      #Identify yourself to GMAIL ESMTP server.
      smtpObj.ehlo()
      #Put SMTP connection in TLS mode and call ehlo again.
      smtpObj.starttls()
      smtpObj.ehlo()
      #Login to service
      smtpObj.login(user=EMAIL_SENDER, password=EMAIL_PASSWORD)
      #Send email
      smtpObj.sendmail(EMAIL_SENDER, receivers, msg.as_string())
      #close connection and session.
      smtpObj.quit();
      return True
    except SMTPException as error:
      print "Error: unable to send email :  {err}".format(err=error)
    return False
