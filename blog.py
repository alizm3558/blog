from flask import Flask,render_template,flash,g,redirect,url_for,session,logging,request #web sunucusunu ayağa kaldırır
from datetime import datetime
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators,ValidationError
from passlib.hash import sha256_crypt
from wtforms.validators import InputRequired, Email
from functools import wraps 

app=Flask(__name__)

app.secret_key="blogkey" #önemli

#veritabanı bilgileri
app.config["MYSQL_HOST"]="localhost" #uzakta olsaydı uzaktaki adı verilirdi
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="blog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"
#---------------------------------------

#kullanıcı kayıt formu, wtForms
class RegisterForm(Form):
    name=StringField("İsim Soyisim:",validators=[validators.length(min=4,max=25)])
    username=StringField("Kullanıcı Adı:",validators=[validators.length(min=5,max=35)])
    email=StringField("Email adresi:",validators=[validators.Email("geçerli mail adresi giriniz")])
    password=PasswordField("Parola",validators=[
        validators.DataRequired(message="Parola belirleyiniz!"),
        validators.EqualTo(fieldname='confrim',message="Parolalar uyuşmuyor")
])
    confrim=PasswordField("Parola doğrula")
#---------------------------------------

mysql=MySQL(app)
 

@app.route('/') #url
def index():
  
   return render_template("index.html") #atama gerçekleştirildi..
@app.route('/hakkimizda') #navbarda tıklandığında URLe '/hakkimizda' yazılacak ki app.route çalışsın!
def about():
    return render_template("hakkimizda.html")
@app.route('/articles')
def articles():
    cursor=mysql.connection.cursor()
    sorgu ="select * from articles"
    result=cursor.execute(sorgu)

    if result>0:
        articles=cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")

   



#kullanıcı giriş decorator
# giriş yapılmadığı halde dashboarda girilmek istenildiği takdirde
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapınız.","danger")
            return redirect(url_for("login"))
    return decorated_function
#-----------------------------------------------------------------------


#kayıt işlemi
@app.route("/register",methods=["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate(): # form.validate() yazılması gerekiyor      
        name=form.name.data
        username=form.username.data
        email=form.email.data
        password=sha256_crypt.encrypt(form.password.data)
        
        cursor=mysql.connection.cursor()
 	    
        denetleme="select * from users where username=%s"
        result=cursor.execute(denetleme,(username,))

        if result>0:
            flash("Kullanıcı mevcuttur.","danger")
            return redirect(url_for("register"))
        else:
            sorgu="insert into users(name,email,username,password) values(%s,%s,%s,%s)"
            cursor.execute(sorgu,(name,email,username,password))
            mysql.connection.commit() #vertabanında herhangi bir güncelleme işlemin yapıldığında commit yapılması gerekiyor

            cursor.close()
            flash("Başarıyla kaydedildi","success")
            return redirect(url_for("login"))
    
    else:
        return render_template("register.html",form=form)
#-----------------------------------------------------------------------------

#articleDetail
@app.route("/articlesDetail/<string:username>/<string:title>")
def articlesDetail(username,title):
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where author=%s and title=%s"
    cursor.execute(sorgu,(username,title))
    article=cursor.fetchone()
    return render_template("articlesDetail.html",article=article)

#------------------------------

#Detay sayfası
@app.route("/article/<string:id>")
@login_required
def article(id):
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where id=%s"
    result=cursor.execute(sorgu,(id,))

    if result>0:
        article2=cursor.fetchone()
        return render_template("article.html",article=article2)
    else:
        return render_template("article.html")


#-------------------------------------------


#login işlemi
class LoginForm(Form): #login form classı
    username=StringField("Kullanıcı Adı",[validators.Optional()])
    password=PasswordField("Parola")


@app.route("/login",methods=["GET","POST"])
def login():
    form=LoginForm(request.form)
    if request.method=="POST":
        username=form.username.data
        password=form.password.data

        cursor=mysql.connection.cursor()
        sorgu="select * from users where username=%s"
        result=cursor.execute(sorgu,(username,))

        if result>0:
            data=cursor.fetchone()
            real_password=data["password"] #veritabanındaki password sütunundaki bilgiyi getiriyor.
            if sha256_crypt.verify(password,real_password):
                flash("Başarıyla giriş yapıldı.","success")

                
                session["logged_in"]=True #session başlatılıyor
                session["username"]=username
                

                return redirect(url_for("index"))
            else:
                flash("Girilen parola yanlıştır.","danger")
                return redirect(url_for("login")) 
        else:
            flash("Böyle bir kullanıcı bulunmamaktadır.","danger")
            return redirect(url_for("login"))


    return render_template("login.html",form=form) # burada üretilen form kalıplarını login sayfasına taşıyoruz
#------------------------------------------------------------


#logout işlemi
@app.route('/logout')
def logout():
    #session temizlenecek
    session.clear()
    flash("Çıkış yapıldı.","success")
    return redirect(url_for("index"))
   
#---------------------------------------------------------------


#dashboard sayfası işlemi
@app.route('/dashboard')
@login_required #giriş yapılmış mı diye login_required decorator'ü kontrol ediyor, giriş yapılmışsa(session başlamışsa) dashboarda yönlendiriyor 
def dashboard():
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where author=%s"
    result=cursor.execute(sorgu,(session["username"],))#tek elemanlı demet olduğunu belirtmek için virgül kullanıyoruz
    if result>0:
        articles=cursor.fetchall()
        return render_template("dashboard.html",articles=articles)

    else:
        return render_template("dashboard.html")
#aslında decorator ile kontrolden ziyade sessionları da kontrol edebiliriz ama bu kötü bir yöntem olur.

#----------------------------------------------------------


#makale ekleme
@app.route('/addarticle',methods=["GET","POST"])
@login_required
def addarticle():
    form=ArticleForm(request.form)# form.validate() koşul kullanırken yazacaksın !
    
    if request.method=="POST" and form.validate():
        title=form.title.data
        content=form.content.data
        username=session["username"]

        cursor=mysql.connection.cursor()
        denetlemeSorgu="select * from articles where author=%s and title=%s"
        result=cursor.execute(denetlemeSorgu,(username,title))
        if result>0:
            flash("Bu başlıklı içerik bulunmaktadır.","danger")

        else:

            sorgu="insert into articles(title,author,content) values(%s,%s,%s)"
            cursor.execute(sorgu,(title,username,content)) #demet halinde alındı
            mysql.connection.commit()

            cursor.close()
            flash("Makaleniz başarıyla kaydedildi.","success")
            return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form=form)
                #çalışıyor

#---------------------------------------------------------------


#makale silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where author=%s and id=%s"
    result=cursor.execute(sorgu,(session["username"],id))

    if result>0:
        sorgu2="delete from articles where id=%s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        flash("Makaleniz siliniştir","success")
        return redirect(url_for("dashboard"))
    else:
        flash("Giriş yapınız.","danger")  
        return redirect(url_for(login))

#--------------------------------------------------------

#makale güncelleme

@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def update(id):
    if request.method=="GET":
        cursor=mysql.connection.cursor()
        sorgu="select * from articles where id=%s and author=%s"
        result=cursor.execute(sorgu,(id,session["username"]))
        
        if result==0:
            flash("Size ait böyle bir makale bulunmamaktadır","danger")
            return redirect(url_for("index"))
        else:
            article=cursor.fetchone()
            form =ArticleForm()

            form.title.data=article["title"]
            form.content.data=article["content"]
            return render_template("update.html",form=form)
        

    else:
        #post request
        form=ArticleForm(request.form)
        newtitle=form.title.data
        newContent=form.content.data

        sorgu2="update articles set title=%s,content=%s where id=%s"
        cursor=mysql.connection.cursor()
        cursor.execute(sorgu2,(newtitle,newContent,id))
        mysql.connection.commit()
        flash("Güncelleme başarılı.","success")
        return redirect(url_for("dashboard"))
        

#----------------------------------------------------

#makale form
class ArticleForm(Form):
    title=StringField("Makale başlığı",validators=[validators.length(min=5,max=100)])
    content=TextAreaField("Makale içeriği",validators=[validators.length(min=10)])
#---------------------------------------------------------------------


#arama url
@app.route('/search',methods=["GET","POST"])
def search():
    if request.method=="GET":
        return redirect(url_for("index"))
    else:
        keyword=request.form.get("keyword") #formdaki keyword adındaki input elemanından değer geliyor
        cursor=mysql.connection.cursor()
        sorgu="select * from articles where title like '%"+keyword+"%'"
        result=cursor.execute(sorgu)

        if result==0:
            flash("Aranan kelimeye uygun makale bulunamadı.","warning")
            return redirect(url_for("articles"))
        else:
            articles=cursor.fetchall()
            return render_template("articles.html",articles=articles)

#-------------------------------------------------------------
    



if __name__=="__main__":
    app.run(debug=True) #web sunucu çalışacak
