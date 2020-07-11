# -*- coding: utf-8 -*-
"""
Created on Sat May 16 16:08:43 2020

@author: Carlos
"""

import urllib
from urllib import request
from http.cookiejar import CookieJar
from bs4 import BeautifulSoup
import os
import re
import base64
from html.parser import HTMLParser
import datetime
import json
import Tweets as tweet
import similarity as similars
import analysis as ela
import sys
import mysql.connector
from urllib.parse import urljoin, urlparse
import requests
from tqdm import tqdm


cj = CookieJar()
opener = request.build_opener(request.HTTPCookieProcessor(cj))

opener.addheaders = [
    ('User-agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0'),
    ('Accept-Language','es,en-us;q=0.7,en;q=0.3')
]


BASE_URL = 'https://www.google.com'
BASE_SEARCH_URL = BASE_URL + '/searchbyimage?%s'

REFERER_KEY = 'Referer'

def is_valid(url):
    print(str(url))
    parsed = urlparse(str(url))
    print(parsed)
    print("Valid es: "+str(bool(parsed.netloc) and bool(parsed.scheme)))
    return bool(parsed.netloc) and bool(parsed.scheme)

def get_all_images(url):
    """
    Returns all image URLs on a single `url`
    """
    urls = []
    try:
        soup = BeautifulSoup(requests.get(url).content, "html.parser",from_encoding="iso-8859-1")
    
        #urls = []
        for img in tqdm(soup.find_all("img"), "Extracting images"):
            img_url = img.attrs.get("src")
            if not img_url:
                # if img does not contain src attribute, just skip
                continue
            # make the URL absolute by joining domain with the URL that is just extracted
            img_url = urljoin(url, img_url)
            try:
                pos = img_url.index("?")
                img_url = img_url[:pos]
            except ValueError:
                pass
            # finally, if the url is valid
            if is_valid(img_url):
                urls.append(img_url)
    except:
        pass
    return urls
  
def download(url, pathname):
    """
    Downloads a file given an URL and puts it in the folder `pathname`
    """
    try:
        # if path doesn't exist, make that path dir
        if not os.path.isdir(pathname):
            os.makedirs(pathname)
        # download the body of response by chunk, not immediately
        response = requests.get(url, stream=True)
        # get the total file size
        file_size = int(response.headers.get("Content-Length", 0))
        # get the file name
        filename = os.path.join(pathname, url.split("/")[-1])
        # progress bar, changing the unit to bytes instead of iteration (default by tqdm)
        progress = tqdm(response.iter_content(1024), f"Downloading {filename}", total=file_size, unit="B", unit_scale=True, unit_divisor=1024)
        with open(filename, "wb") as f:
            for data in progress:
                # write data read to the file
                f.write(data)
                # update the progress bar manually
                progress.update(len(data))
    except:
        pass

def get_referer_index():
    i = 0
    for k, v in opener.addheaders:
        if k == REFERER_KEY:
            return i
        i += 1
    else:
        return None


def set_referer(url):
    cur = get_referer_index()
    if cur is not None:
        del opener.addheaders[cur]
    opener.addheaders.append(
        (REFERER_KEY, url)
    )

def search_image(url):
  try:
    params = {
        'image_url': url,
        'hl': 'es',
        }
    query = BASE_SEARCH_URL % urllib.parse.urlencode(params)
    print(query)
    f = opener.open(query)
    url = f.url
    f = opener.open(url)
    html = f.read()
    set_referer(f.url)
    return html
  except:
    pass

def get_similar_image_urls(html,lastid):
    soup = BeautifulSoup(html,'html.parser')
    
    with open("config.json") as json_data_file:
        data = json.load(json_data_file)
    mydb = mysql.connector.connect(
            host=data["mysql"]["host"],
            user=data["mysql"]["user"],
            password=data["mysql"]["passwd"],
            database=data["mysql"]["db"]
    )
    
    with open("config.json") as json_data_file:
        data = json.load(json_data_file)
    try: 
        json_string='''{"images":[''';

        for item in soup.find('div', id="iur").find_all('a'):   
            url = item.get('href')
            soup2= BeautifulSoup(str(item),'html.parser')
            json_string=json_string+'''{"url":'''+'''"'''+item.get('href')+'''"'''+''',''';
            for item2 in soup2.find('g-img').findAll('img'):
              #Coger el id de la imagen
              json_string=json_string+'''"idimage":'''+'''"'''+item2.get('id')+'''"'''+''',"src":'''+'''"'''+item2.get('src')+'''"'''+''',"title":'''+'''"'''+item2.get('title')+'''"'''+'''},''';
              mycursor = mydb.cursor()
              sql = "INSERT INTO googlesearch (tweetid,url,title,imageName,src) VALUES (%s,%s,%s,%s,%s)"
              val = (lastid,item.get('href'),item2.get('title'),item2.get('id'),item2.get('src'))
              mycursor.execute(sql, val)
              mydb.commit()  
        json_string=json_string+''']}''';    
        json_string=json_string.replace(",]", "]");
        json_images=json_string
        data=json.loads(str(json_images))
        soup3 = BeautifulSoup(html,'html.parser')
        scripts=soup3.find_all('script')
        now = datetime.datetime.now()
        now.strftime("%Y%m%d%H%M%S")
        import time
        timestr = time.strftime("%Y%m%d-%H%M%S")
        path = "./"+sys.argv[1]+"/downloadsimages"+str(timestr)
        mycursor = mydb.cursor()
        sql = "UPDATE googlesearch SET pathFile = %s WHERE tweetid= %s"
        val = (path,lastid)
        mycursor.execute(sql, val)
        mydb.commit()  
        
        if not os.path.exists(path):
            os.makedirs(path)

        for nonce in scripts:
            if nonce.has_attr('nonce'):
                               
                if str(nonce).strip().find("data:image/jpeg;base64")>0 or str(nonce).strip().find("data:image/png;base64")>0:
 
                 r = str(nonce).split('<script')[1].split('>')[1].strip('</script>')
                 images=str(r)[19:]
                 piece="\';"
                 subs='data:image/jpeg;base64,'
                 images=images.replace(subs,"")
                 subs='data:image/png;base64,'
                 images=images.replace(subs,"")
                 imageName=images[images.find(piece)+2:]
                 subStr=";_setImagesSrc(ii,s);})();"
                 subStr2="var ii=[";
                 imageName=imageName.replace(subStr,"").replace(subStr2,"").replace("]","").replace("\'","").replace(",","_")
                 images=images[:-(len(images)-(images.find(piece)))].replace('\\x3d','=')
                 imgdata = base64.b64decode(images)
                 #print(imageName)
                 with open(path+"/"+imageName+".jpg", "wb") as fh:
                     fh.write(imgdata)
        
        for item77 in soup.find('div', id="rso").findAll('a', {'class':"rGhul"}): 
           url = item77.get('href')
           #print(str(item77))
           if item77.has_attr('ping'):
               
              ping1=str(item77.get('ping').replace("%3D","=").replace("%26","&").replace("%3F","?")[46:])
              ping2=ping1.split("imgrefurl")
              ping3=ping2[0][:-1]
              ping4=ping2[1][1:]
           else:
               ping1=str(item77.get('href')[15:])
               ping2=ping1.split("imgrefurl")
               ping3=ping2[0][:-1]
               ping4=ping2[1][1:]
           soup5= BeautifulSoup(str(item77),'html.parser')
           for item5 in soup5.find('g-img').findAll('img'):
               mycursor = mydb.cursor()
               sql = "INSERT INTO googlesearch (tweetid,url,title,ping,imageName,src) VALUES (%s,%s,%s,%s,%s,%s)"
               val = (lastid,item77.get('href'),str(ping3),str(ping4),item5.get('id'),item5.get('src'))
               mycursor.execute(sql, val)
               mydb.commit()
               mycursor = mydb.cursor()
               sql = "UPDATE googlesearch SET pathFile = %s WHERE tweetid= %s"
               val = (path,lastid)
               mycursor.execute(sql, val)
               mydb.commit()  
        return data; 
            #yield urllib.parse.parse_qs(urllib.parse.urlparse(url).query)['imgurl']
    except AttributeError:
        print("Google has not found anything")
        pass
    
def main():
    with open("config.json") as json_data_file:
        data = json.load(json_data_file)
    mydb = mysql.connector.connect(
            host=data["mysql"]["host"],
            user=data["mysql"]["user"],
            password=data["mysql"]["passwd"],
            database=data["mysql"]["db"]
    )
    
    tweet.get_all_tweets(sys.argv[1])
    path="./"+sys.argv[1]
    os.mkdir(path)
    with open(r"C:\Users\Carlos\Desktop\TFM\MediaFakes\tweets_clean.csv") as f:
     lis = [line.split() for line in f]        # create a list of lists
     for i, x in enumerate(lis):              #print the list items 
       #print("line{0} = {1}".format(i, x))
       s= ''.join(x)
       ##print(len(s))
       if(len(s.split("||")[0])):
           url=s.split("||")[0]
           url=url.replace("\"","")
       else:
           url=""
       if(len(s.split("||")[1])):  
           datetime=s.split("||")[1]
       else:
           datetime=""
       if(len(s.split("||")[2])):
           content=s.split("||")[2]
       else:
           content=""
       html = search_image(url)
       mycursor = mydb.cursor()

       sql = "INSERT INTO tweets (account,imagetweet,content,datetweet) VALUES (%s,%s,%s,%s)"
       val = (sys.argv[1],url,content.replace("\"",""),datetime)
       mycursor.execute(sql, val)
       mydb.commit()
       lastid=mycursor.lastrowid
       contentdir=""
       pathFile=""
       data=get_similar_image_urls(html,lastid)
       
       if data!=0:
           mycursor = mydb.cursor()
           sql="SELECT pathFile FROM googlesearch where tweetid=%s LIMIT 1"
           mycursor.execute(sql,(lastid,))
           myresult = mycursor.fetchone()
           longurl=len(url.rsplit('/'))
           if myresult is not None:
               import urllib.request
               urllib.request.urlretrieve(url, str(myresult[0])+"/"+url.rsplit('/')[longurl-1])
               
               contentdir = os.listdir(str(myresult[0]))
               origin=""
               for f in contentdir:
                   if os.path.isfile(os.path.join(str(myresult[0]), f)) and f.endswith('.jpg') and not f.startswith('dimg'):
                       ##print(f)
                       origin=str(myresult[0])+"/"+f
                       ##print(origin)
                       contentdir = os.listdir(str(myresult[0]))
                       pathFile=str(myresult[0])
                       for fi in contentdir:
                            if os.path.isfile(os.path.join(str(myresult[0]), fi)) and fi.endswith('.jpg') and fi.startswith('dimg'):
                                ##print(fi)
                                destiny=str(myresult[0])+"/"+fi
                                ##print(destiny)
                                result=similars.compare_images(origin,destiny,str(myresult[0]))
                               
                                if(result<5):
                                    mycursor = mydb.cursor()
                                    sql="SELECT ping FROM googlesearch where tweetid=%s and imageName=%s and pathFile=%s LIMIT 1"
                                    
                                    mycursor.execute(sql,(lastid,str(fi[:-4]),str(myresult[0])))
                                    myresult60 = mycursor.fetchone()
                                    myres=myresult60
                                    if myres is not None:
                                        os.remove(str(myresult[0])+"/resized.jpg")
                                    else:
                                        os.remove(str(myresult[0])+"/"+fi)
                                        os.remove(str(myresult[0])+"/resized.jpg")
                                    mycursor = mydb.cursor()
                                    sql = "UPDATE googlesearch SET similarity=%s WHERE tweetid=%s and imageName=%s"
                                    value = (str(result),lastid,str(fi[:-4]))
                                    ##print(value)
                                    mycursor.execute(sql, value)
                                    mydb.commit()
                                else:
                                    os.remove(str(myresult[0])+"/resized.jpg")
                                    mycursor = mydb.cursor()
                                    sql = "UPDATE googlesearch SET similarity = %s WHERE tweetid= %s and imageName=%s"
                                    value = (str(result),lastid,str(fi[:-4]))
                                    ##print(value)
                                    mycursor.execute(sql, value)
                                    mydb.commit()
       ##print(pathFile)
       if pathFile!='':
           num_files = len([f for f in os.listdir(pathFile)if os.path.isfile(os.path.join(pathFile, f))])
           ##print(num_files)
           if num_files==1:
               mycursor = mydb.cursor()
               sql = "UPDATE tweets SET isFakeNew=%s WHERE id=%s"
               value = (0,lastid)
               ##print(value)
               mycursor.execute(sql, value)
               mydb.commit()
           else:
              contentdir = os.listdir(pathFile)
              ###print(contentdir)
              for fi in contentdir:
                  if fi.count("dimg_")>1:
                     os.remove(str(pathFile)+"/"+fi)
              if len([name for name in os.listdir(pathFile) if os.path.isfile(name)])==1:
                  mycursor = mydb.cursor()
                  sql = "UPDATE tweets SET isFakeNew=%s WHERE id=%s"
                  value = (0,lastid)
                  mycursor.execute(sql, value)
                  mydb.commit()
              else:
                 contentdir = os.listdir(pathFile)
                 for fi in contentdir:
                   if fi.startswith('dimg'):
                     mycursor2 = mydb.cursor()
                     sql4="SELECT similarity FROM googlesearch where tweetid=%s and imageName=%s and pathFile=%s"
                     value=(lastid,str(fi[:-4]),str(myresult[0]))
                     mycursor2.execute(sql4,value)
                     myresult90 = mycursor2.fetchone()
                     if myresult90 is not None and float(myresult90[0])<5.0:
                         os.remove(str(myresult[0])+"/"+fi)
                 count=0
                 for path in os.listdir(pathFile):
                    if os.path.isfile(os.path.join(str(myresult[0]), path)):
                        count += 1
                 #if len([name for name in os.listdir(str(myresult[0])) if os.path.isfile(name)])==1:
                 if count==1:
                     mycursor7 = mydb.cursor()
                     sql = "UPDATE tweets SET isFakeNew=%s WHERE id=%s"
                     value = (0,lastid)
                     mycursor7.execute(sql, value)
                     mydb.commit()
                 else:
                    contentdir = os.listdir(str(myresult[0]))
                    myresult100=""
                    origin=""
                    for fi in contentdir:
                      if os.path.isfile(os.path.join(str(myresult[0]), f)) and f.endswith('.jpg') and not f.startswith('dimg'):
                        origin=str(myresult[0])+"/"+f
                    for fi in contentdir:
                     print("Origen es:" +origin)
                     if fi.startswith('dimg_'):
                        mycursor2 = mydb.cursor()
                        print(mycursor2)
                        sql4="SELECT title FROM googlesearch where tweetid=%s and imageName=%s and pathFile=%s"
                        value=(lastid,str(fi[:-4]),str(myresult[0]))
                        print(value)
                        print(mycursor2.execute(sql4,value))
                        myresult100 = mycursor2.fetchone()
                        print(myresult100)
                        if myresult100 is not None:
                            # get all images
                            print("Procesando: "+str(myresult100[0]))
                            imgs = get_all_images(str(myresult100[0]))
                            print("Las imagenes son: "+str(imgs))
                            for img in imgs:
                                # for each image, download it
                               specialstring="*"
                               if img.endswith('jpg') or img.endswith('png'):
                                if specialstring not in img:
                                  download(img, str(myresult[0]))
                                  
       mycursor7 = mydb.cursor()
       print(mycursor7)
       sql4="SELECT imagetweet FROM tweets where id=%s"
       print(mycursor7.execute(sql4,(lastid,)))
       myresult200 = mycursor7.fetchone()
       print(myresult200)
       result22 = str(myresult200).split('/')[-1]
       print(result22)
       ##try:
       mycursor = mydb.cursor()
       sql="SELECT pathFile FROM googlesearch where tweetid=%s LIMIT 1"
       mycursor.execute(sql,(lastid,))
       print(lastid)
       myresult = mycursor.fetchone()
       if mycursor.rowcount>0:
           origin=str(myresult[0])+"/"+str(result22)
           from PIL import Image, ExifTags
           img = Image.open(origin.replace("',)",""))
           #img = Image.open(os.path.join(root, origin))
           if img._getexif() is not None:
               exif = { ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS }
               if exif is not None:
                   print(exif)
                   mycursor9 = mydb.cursor()
                   sql = "UPDATE tweets SET metadata=%s WHERE id=%s"
                   value = (exif,lastid)
                   mycursor9.execute(sql, value)
                   mydb.commit()
           contentdir = os.listdir(myresult[0])
           for fi2 in contentdir:
            print("El último id es:" +str(lastid))
            if not fi2.startswith('dimg_') and fi2 not in origin:
               destiny=str(myresult[0])+"/"+fi2
               print("El origen es: "+origin)
               print("El destino es: " +destiny)
               result=similars.compare_images(origin.replace("',)",""),destiny,str(myresult[0]))
               if result <= 80:
                   os.remove(str(myresult[0])+"/"+fi2)
                   if os.path.exists(str(myresult[0])+"/resized.jpg"):
                     os.remove(str(myresult[0])+"/resized.jpg")
               else:
                   if os.path.exists(str(myresult[0])+"/resized.jpg"):
                     os.remove(str(myresult[0])+"/resized.jpg")
           ori=str(result22)
           origin=str(myresult[0])+"/"+ori.replace("',)","")
           if origin.endswith('.jpg'):
               print("Se va a hacer el ELA con " +origin+" y "+path)
               elareturns=ela.level2(origin.replace("',)",""),myresult[0]) 
               mycursor11 = mydb.cursor()
               sql = "UPDATE tweets SET metadata=%s,isManipulated=%s,ELA=%s WHERE id=%s"
               if elareturns[2]!="1" and elareturns[1]==0:
                   value = (elareturns[2],elareturns[1],elareturns[0],lastid)
                   mycursor11.execute(sql, value)
                   mydb.commit()
               else:
                   value = ("",elareturns[1],elareturns[0],lastid)
                   mycursor11.execute(sql, value)
                   mydb.commit()
                   
               
       ##except:
         #print("Error")
         ##pass
                        
if __name__ == '__main__':
    main()