from flask import Flask,render_template,url_for,redirect,request,flash,session
from otp import genotp
from cmail import sendmail
from tokens import encode,decode
import os
import re
import razorpay
import mysql.connector
mydb=mysql.connector.connect(host='localhost',user='root',password='Taneem_2002',db='ecommi')
# mydb=connnection.MYSQLConnection(host='localhost',user='root',password='Taneem_2002',db='ecommi')
app=Flask(__name__)
app.config['SESSION_TYPE']='filesystem'
app.secret_key='ecom$tan111'
RAZORPAY_KEY_ID='rzp_test_BdYxoi5GaEITjc'
RAZORPAY_KEY_SECRET='H0FUH2n4747ZSYBRyCn2D6rc'
client=razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))

@app.route('/')
def home():
    return render_template('welcome.html')

@app.route('/index')
def index():
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,quantity,price,category,image_name from items')
        items_data=cursor.fetchall() # to retrive all the items from the items table
    except Exception as e:
        print(e)
        flash('something went wrong')
        return redirect(url_for('home'))
    else:
        return render_template('index.html',items_data=items_data)
    

@app.route('/admincreate',methods=['GET','POST'])
def admincreate():
    if request.method=='POST':
        #print(request.form) form ka data kaisa aata hey kako dekhnay aisa likhtey
        aname=request.form['username']
        aemail=request.form['email']
        password=request.form['password']
        address=request.form['address']
        status_accept=request.form['agree']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(email) from admincreate where email=%s',[aemail])
        email_count=cursor.fetchone()
        if email_count[0]==0:
            otp=genotp()
            admindata={'aname':aname,'aemail':aemail,'password':password,'address':address,'accept':status_accept,'aotp':otp}
            subject='TQ for registering in taneemkart'
            body=f'Ecommers verification otp for admin regrestation {otp}'
            sendmail(to=aemail,subject=subject,body=body)
            flash('OTP has sent to given mail')
            return redirect(url_for('otp',padata=encode(data=admindata)))
        elif email_count[0]==1:
            flash('email already exist please login')
            return redirect(url_for('adminlogin'))
    return render_template('admincreate.html')

@app.route('/otp/<padata>',methods=['GET','POST'])
def otp(padata):
    if request.method=='POST':
        fotp=request.form['otp']
        try:
            d_data=decode(data=padata)
        except Exception as e:
            print(e)
            flash('something went wrong')
            return redirect(url_for('admincreate'))
        else:
            if fotp==d_data['otp']:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into admincreate(email,username,password,address,accept) values(%s,%s,%s,%s,%s)',[d_data['aemail'],d_data['aname'],d_data['password'],d_data['address'],d_data['accept']])
                mydb.commit()
                cursor.close()
                flash('reg success')
                return redirect(url_for('login'))
            else:
                flash('otp is wrong')
                return redirect(url_for('admincreate'))
    return render_template('adminotp.html')

@app.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    if not session.get('admin'):
        if request.method=='POST':
            log_email=request.form['email']
            log_password=request.form['password']
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select count(email) from admincreate where email=%s',[log_email])
                stored_emailcount=cursor.fetchone()
            except Exception as e:
                print(e)
                flash('something went wrong connection error')
                return redirect(url_for('adminlogin'))
            else:
                if stored_emailcount[0]==1:
                    cursor.execute('select password from admincreate where email=%s',[log_email])
                    stored_password=cursor.fetchone()
                    print(stored_password)
                    if log_password==stored_password[0].decode('utf-8'):
                        print(session)
                        session['admin']=log_email
                        if not session.get(log_email):
                            session[log_email]={}
                        print(session)
                        return redirect(url_for('adminpanel'))
                    else:
                        flash('wrong pass')
                        return redirect(url_for('adminlogin'))
                else:
                    flash('wrong email')
                    return redirect(url_for('adminlogin'))
        return render_template('adminlogin.html')
    else:
        return redirect(url_for('adminpanel'))

@app.route('/adminpanel')
def adminpanel():
    if session.get('admin'):
        return render_template('adminpanel.html')
    else:
        return redirect(url_for('adminlogin'))


@app.route('/adminforgot',methods=['GET','POST'])
def adminforgot():
    if request.method=='POST':
        forgot_email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(email) from admincreate where email=%s',[forgot_email])
        stored_email=cursor.fetchone()
        if stored_email[0]==1:
            subject='reset link for admin '
            body=f"click on the link to update ur password:{url_for('ad_password_update',token=encode(data=forgot_email),_external=True)}" # _external=true likhay nai tho o data pura text kay naad jata
            sendmail(to=forgot_email,subject=subject,body=body)
            flash(f'reset link has sent to given mail {forgot_email}')
            return redirect(url_for('adminforgot'))
        elif stored_email[0]==0:
            flash('no email regestered please check')
            return redirect(url_for('adminlogin'))
    return render_template('forgot.html')

@app.route('/ad_password_update/<token>',methods=['GET','POST'])
def ad_password_update(token):
    if request.method=='POST':
        try:
            npassword=request.form['npassword']
            cpassword=request.form['cpassword']
            dtoken=decode(data=token) #detoken the encrpt email
        except Exception as e:
            print(e)
            flash('something went wrong')
            return redirect(url_for('adminlogin'))
        else:
            if npassword==cpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update admincreate set password=%s where email=%s',[npassword,dtoken])
                mydb.commit()
                flash('password updated succesfully')
                return redirect(url_for('adminlogin'))
            else:
                flash('password mismaitches')
                return redirect(url_for('ad_password_update',token=token))
    return render_template('newpassword.html')

@app.route('/additem',methods=['GET','POST'])
def additem():
    if session.get('admin'):
        if request.method=='POST':
            title=request.form['title']
            des=request.form['Discription']
            quantity=request.form['quantity']
            price=request.form['price']
            category=request.form['category']
            img_file=request.files['file']
            print(img_file)
            print(img_file.filename)
            print(img_file.filename.split('.'))
            img_name=genotp()+'.'+img_file.filename.split('.')[-1]
             # creating file name using user extension
            # to store the image in static folder we need to  get the path without system varies
            drname=os.path.dirname(os.path.abspath(__file__)) # D:\PFSD7\ecom
            static_path=os.path.join(drname,'static') # D:\PFSD7\ecom\static
            img_file.save(os.path.join(static_path,img_name))
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into items(item_id,item_name,description,price,quantity,category,image_name,added_by) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s)',[title,des,price,quantity,category,img_name,session.get('admin')])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('something went wring')
                return redirect(url_for('additem'))
            else:
                flash(f'{title[:10]} added succesfully')
                return redirect(url_for('additem'))
        return render_template('additem.html')
    else:
        return redirect(url_for('adminlogin'))

@app.route('/viewall_items')
def viewall_items():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,image_name from items where added_by=%s',[session.get('admin')])
            stored_items=cursor.fetchall()
        except Exception as e:
            print(e)
            flash('connection problem')
            return redirect(url_for('adminpanel'))
        else:
            return render_template('viewall_items.html',stored_items=stored_items)
    else:
        return redirect(url_for('adminlogin'))
    
@app.route('/view_item/<item_id>')
def view_item(item_id):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,description,price, quantity,category,image_name from items where item_id=uuid_to_bin(%s)',[item_id])
            item_data=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('connection error')
            return redirect(url_for('viewall_items'))
        else:
            return render_template('view_item.html',item_data=item_data)
    else:
        return redirect(url_for('adminlogin'))


@app.route('/delete_item/<item_id>')
def delete_item(item_id):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select image_name from items where item_id=uuid_to_bin(%s)',[item_id])
            stored_image=cursor.fetchone()
            print(stored_image)
            drname=os.path.dirname(os.path.abspath(__file__)) # D:\PFSD7\ecom
            static_path=os.path.join(drname,'static') # D:\PFSD7\ecom\static
            if stored_image[0] in os.listdir(static_path):
                os.remove(os.path.join(static_path,stored_image[0]))
            cursor.execute('delete from items where item_id=uuid_to_bin(%s)',[item_id])
            mydb.commit()
            cursor.close()
        except Exception as e:
            print(e)
            flash('could not delete')
            return redirect(url_for('viewall_items'))
        else:
            flash('items deletes succesfully')
            return redirect(url_for('viewall_items'))
    else:
        return redirect(url_for('adminlogin'))
    
@app.route('/update_item/<item_id>',methods=['GET','POST'])
def update_item(item_id):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,description,price, quantity,category,image_name from items where item_id=uuid_to_bin(%s)',[item_id])
            item_data=cursor.fetchone() #(item_id,item)
        except Exception as e:
            print(e)
            flash('connection error')
            return redirect(url_for('viewall_items'))
        else:
            if request.method=='POST':
                title=request.form['title']
                des=request.form['Description']
                quantity=request.form['quantity']
                price=request.form['price']
                category=request.form['category']
                img_file=request.files['file']# ' '
                filename=img_file.filename # to fetch the filename
                print(filename,11)
                if filename == '':
                    img_name=item_data[6] # updating with old name
                else:
                    img_name=genotp()+'.'+filename.split('.')[-1] #creating new file name if new image is uploded
                    drname=os.path.dirname(os.path.abspath(__file__)) # D:\PFSD7\ecom
                    static_path=os.path.join(drname,'static') # D:\PFSD7\ecom\static
                    if item_data[6] in os.listdir(static_path):
                        os.remove(os.path.join(static_path,item_data[6]))
                    img_file.save(os.path.join(static_path,img_name))
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update items set item_name=%s,description=%s,price=%s,quantity=%s,category=%s,image_name=%s where item_id=uuid_to_bin(%s)',[title,des,price,quantity,category,img_name,item_id])
                mydb.commit()
                cursor.close()
                flash('Item updated succesfully')
                return redirect(url_for('view_item',item_id=item_id))
            return render_template('update_item.html',data=item_data)
    else:
        return redirect(url_for('adminlogin'))

@app.route('/adminprofile_update',methods=['GET','POST'])
def adminprofile_update():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select username, address,ph_no, dp_image from admincreate where email=%s',[session.get('admin')])
            admin_data=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('something went wrong')
            return redirect(url_for('adminpanel'))
        else:
            if request.method=='POST':
                adminname=request.form['adminname']
                address=request.form['address']
                ph_no=request.form['ph_no']
                pro_file=request.files['file']
                fname=pro_file.filename 
                print(fname,14)
                if fname=='':
                    img_proname=admin_data[3]
                    print(img_proname,1111111111111111)
                else:
                    img_proname=genotp()+'.'+fname.split('.')[-1] #creating new file name if new image is uploded
                    print("Profile name:",img_proname)
                    drname=os.path.dirname(os.path.abspath(__file__)) # D:\PFSD7\ecom
                    static_path=os.path.join(drname,'static') # D:\PFSD7\ecom\static
                    if admin_data[3] in os.listdir(static_path):
                        os.remove(os.path.join(static_path,admin_data[3]))
                    pro_file.save(os.path.join(static_path,img_proname))
                cursor.execute('update admincreate set username=%s, address=%s,ph_no=%s, dp_image=%s where email=%s',[adminname,address,ph_no,img_proname,session.get('admin')])
                mydb.commit()
                cursor.close()
                return redirect(url_for('adminpanel'))
            return render_template('adminupdate.html',admin_data=admin_data)
    else:
        return redirect(url_for('adminlogin'))

@app.route('/adminlogout')
def adminlogout():
    if session.get('admin'):
        session.pop('admin')
        return redirect(url_for('index'))
    return redirect(url_for('adminlogin'))

@app.route('/usercreate',methods=['GET','POST'])
def usercreate():
    if request.method=='POST':
        uname=request.form['name']
        uemail=request.form['email']
        uaddress=request.form['address']
        upassword=request.form['password']
        usergender=request.form['usergender']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(user_email) from usercreate where user_email=%s',[uemail])
        uemail_count=cursor.fetchone()
        if uemail_count[0]==0:
            uotp=genotp()
            userdata={'uname':uname,'uemail':uemail,'upassword':upassword,'uaddress':uaddress,'usergender':usergender,'uotp':uotp}
            subject='TQ for registering in taneemkart'
            body=f'Ecommers verification otp for user regrestation {uotp}'
            sendmail(to=uemail,subject=subject,body=body)
            flash('OTP has sent to given mail')
            return redirect(url_for('uotp',pudata=encode(data=userdata)))
        elif uemail_count[0]==1:
            flash('email already exist please login')
            return redirect(url_for('userlogin'))
    return render_template('usersignup.html')

@app.route('/uotp/<pudata>',methods=['GET','POST'])
def uotp(pudata):
    if request.method=='POST':
        fuotp=request.form['otp']
        try:
            d_udata=decode(data=pudata)
        except Exception as e:
            print(e)
            flash('something went wrong')
            return redirect(url_for('usercreate'))
        else:
            if fuotp==d_udata['uotp']:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into usercreate( user_email,username,password,address,gender) values(%s,%s,%s,%s,%s)',[d_udata['uemail'],d_udata['uname'],d_udata['upassword'],d_udata['uaddress'],d_udata['usergender']])
                mydb.commit()
                cursor.close()
                flash('reg success')
                return redirect(url_for('userlogin'))
            else:
                flash('otp is wrong')
                return redirect(url_for('usercreate'))
    return render_template('userotp.html')

@app.route('/userlogin',methods=['GET','POST'])
def userlogin():
    if not session.get('user'):
        if request.method=='POST':
                log_uemail=request.form['email']
                log_upassword=request.form['password']
                try:
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('select count(user_email) from usercreate where user_email=%s',[log_uemail])
                    stored_emailcount=cursor.fetchone()
                except Exception as e:
                    print(e)
                    flash('something went wrong connection error')
                    return redirect(url_for('userlogin'))
                else:
                    if stored_emailcount[0]==1:
                        cursor.execute('select password from usercreate where user_email=%s',[log_uemail])
                        stored_password=cursor.fetchone()
                        print(stored_password)
                        if log_upassword==stored_password[0].decode('utf-8'):
                            print(session)
                            session['user']=log_uemail
                            if not session.get(log_uemail):
                                session[log_uemail]={}
                            print(session)
                            return redirect(url_for('index')) # ya asal readreview page aanaaa
                        else:
                            flash('wrong pass')
                            return redirect(url_for('userlogin'))
                    else:
                        flash('wrong email')
                        return redirect(url_for('userlogin'))
        return render_template('userlogin.html')
    else:
        return redirect(url_for('index'))
    
@app.route('/userforgot',methods=['GET','POST'])
def userforgot():
    if request.method=='POST':
        forgot_useremail=request.form['uemail']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(user_email) from usercreate where user_email=%s',[forgot_useremail])
        stored_email=cursor.fetchone()
        if stored_email[0]==1:
            subject='reset link for user'
            body=f"click on the link to update ur password:{url_for('user_password_update',token=encode(data=forgot_useremail),_external=True)}" # _external=true likhay nai tho o data pura text kay naad jata
            sendmail(to=forgot_useremail,subject=subject,body=body)
            flash(f'reset link has sent to given mail {forgot_useremail}')
            return redirect(url_for('userforgot'))
        elif stored_email[0]==0:
            flash('no email regestered please check')
            return redirect(url_for('userlogin'))
    return render_template('userforfot.html')

@app.route('/user_password_update/<token>',methods=['GET','POST'])
def user_password_update(token):
    if request.method=='POST':
        try:
            npassword=request.form['npassword']
            cpassword=request.form['cpassword']
            dtoken=decode(data=token) #detoken the encrpt email
        except Exception as e:
            print(e)
            flash('something went wrong')
            return redirect(url_for('userlogin'))
        else:
            if npassword==cpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update usercreate set password=%s where user_email=%s',[npassword,dtoken])
                mydb.commit()
                flash('password updated succesfully')
                return redirect(url_for('userlogin'))
            else:
                flash('password mismaitches')
                return redirect(url_for('ad_password_update',token=token))
    return render_template('newuserpassword.html')

@app.route('/userlogout')
def userlogout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('index'))
    return redirect(url_for('userlogin'))

@app.route('/readerview.html')
def readerview():
    if session.get('user'):
        return render_template('readerview.html')
    else:
        return redirect('userlogin')
    
@app.route('/category/<type>')
def category(type):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,quantity,price,category,image_name from items where category=%s',[type])
        items_data=cursor.fetchall() # to retrive all the items from the items table
    except Exception as e:
        print(e)
        flash('something went wrong')
        return redirect(url_for('home'))
    return render_template('dashboard.html',items_data=items_data)


@app.route('/description/<itemid>')
def description(itemid):
    if not session.get('user'):
        return redirect(url_for('userlogin'))
    else:
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,description,quantity,price,category,image_name from items where item_id=uuid_to_bin(%s)',[itemid])
            item_data=cursor.fetchone() # to retrive all the items from the items table
        except Exception as e:
            print(e)
            flash('something went wrong')
            return redirect(url_for('index'))
        return render_template('description.html',item_data=item_data)

@app.route('/addcart/<itemid>/<name>/<price>/<qyt>/<image>/<categoty>')
def addcart(itemid,name,price,qyt,image,categoty):
    if not session.get('user'):
        return redirect(url_for('userlogin'))
    else:
        print(session)
        if itemid not in session['user']:
            session[session.get('user')][itemid]=[name,price,1,image,categoty,qyt]
            session.modified=True
            print(session)
            flash(f'{name} added to cart')
            return redirect(url_for('index'))
        session[session.get('user')][itemid][2]+=1
        flash('item already exist in cart')
        return redirect(url_for('index'))
    

@app.route('/viewcart')
def viewcart():
    if not session.get('user'):
        return redirect(url_for('userlogin'))
    else:
        if session.get(session.get('user')):
            items=session[session.get('user')]
            print(items)
        else:
            items='empty'
        if items=='empty':
            flash('no product added to cart')
            return redirect(url_for('index'))
        return render_template('cart.html',items=items)

@app.route('/removecart_item/<itemid>')
def removecart_item(itemid):
    if not session.get('user'):
        return redirect(url_for('userlogin'))
    else:
        session.get(session.get('user')).pop(itemid)
        session.modified=True
        print(session)
        flash('item removes sussfully from cart')
        return redirect(url_for('viewcart'))

@app.route('/pay/<itemid>/<name>/<float:price>',methods=['GET','POST'])
def pay(itemid,name,price):
    try :
        qyt=int(request.form['qyt'])
        amount=price*100 # converting price into paise
        total_price=amount*qyt
        print(amount,qyt,total_price)
        print(f'creating  payment for item:{itemid},name:{name},price:{price}') #creating razor pay order
        order=client.order.create({
            'amount':total_price,
            'currency':'INR',
            'payment_capture':'1' 
        })
        print(f'order created:{order}')
        return render_template('pay.html',order=order,itemid=itemid,name=name,price=price,qyt=qyt)
    except Exception as e:
        print(e)
        print(f'error creating order: {str(e)}')
        flash('error in payment')
        return redirect(url_for('index'))

@app.route('/success',methods=['POST'])
def success():
    # extract payment details from the form
    payment_id=request.form.get('razorpay_payment_id')
    order_id=request.form.get('razorpay_order_id')
    signature=request.form.get('razorpay_signature')
    name=request.form.get('name')
    itemid=request.form.get('itemid')
    price=request.form.get('price')
    qyt=request.form.get('qyt')
    #verification process
    params_dict={
        'razorpay_order_id':order_id,
        'razorpay_payment_id':payment_id,
        'razorpay_signature':signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('insert into orders(itemid,item_name,total_price,user,qty) values(uuid_to_bin(%s),%s,%s,%s,%s)',[itemid,name,price,session.get('user'),qyt])
        mydb.commit()
        cursor.close()
        flash('order placed succesfully')
        # return 'success'
        return redirect(url_for('orders'))
    except razorpay.errors.SignatureVerificationError:
        return 'Pay verification failes',400

@app.route('/orders')
def orders():
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select orderid,bin_to_uuid(itemid),item_name,total_price,user,qty from orders where user=%s',[session.get('user')])
            ordlist=cursor.fetchall()
        except Exception as e:
            print(e,'error in fetching orders')
            flash('could not fetch orders')
            return redirect(url_for('index'))
        else:
            return render_template('orders.html',ordlist=ordlist)
    else:
        return redirect('userlogin')

@app.route('/addreview/<itemid>',methods=['GET','POST'])
def addreview(itemid):
    if session.get('user'):
        if request.method=='POST':
            title=request.form['title']
            reviewtext=request.form['review']
            rating=request.form['rate']
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into reviews(username,itemid,title,review,rating) values(%s,uuid_to_bin(%s),%s,%s,%s)',[session.get('user'),itemid,title,reviewtext,rating])
                mydb.commit()
            except Exception as e:
                print(f"Error in inserting review:{e}")
                flash('cant add review please try after some time')
                return redirect(url_for('description',itemid=itemid))
            else:
                cursor.close()
                flash('review has submitted')
                return redirect(url_for('description',itemid=itemid))
        else:
            return render_template('review.html')
    else:
        return redirect(url_for('userlogin'))
    
@app.route("/readreview/<itemid>")
def readreview(itemid):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,description,quantity,price,category,image_name from items where item_id=uuid_to_bin(%s)',[itemid])
        item_data=cursor.fetchone()
        cursor.execute('select * from reviews where itemid=uuid_to_bin(%s)',[itemid])
        data=cursor.fetchall()
    except Exception as e:
        print(e)
        flash('could not fetach data')
        return redirect(url_for('index'))
    finally:
        cursor.close()
    return render_template('readreview.html',item_data=item_data,data=data)

@app.route('/contactus',methods=['GET','POST'])
def contactus():
    if session.get('user'):
        if request.method=='POST':
            email=request.form['email']
            description=request.form['description']
            title=request.form['title']
            
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into contactus(name,email,message) values(%s,%s,%s)',[email,title,description])
                mydb.commit()
            except Exception as e:
                print(f"Error in inserting review:{e}")
                flash('cant add  please try after some time')
                return redirect(url_for('index'))
            else:
                cursor.close()
                flash('submitted')
                return redirect(url_for('index'))
        else:
            return render_template('contact.html')
    else:
        return redirect(url_for('userlogin'))
    

@app.route('/search',methods=['GET','POST'])
def search():
    if session.get('user'):
        try:
            if request.method=='POST':
                sitems=request.form['search']
                strg=['A-Za-z0-9']
                pattern=re.compile(f'^{strg}',re.IGNORECASE)
                if (pattern.match(sitems)):
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('select * from items where item_name like %s or description like %s or price like %s',['%'+sitems+'%','%'+sitems+'%','%'+sitems+'%'])
                    items_data=cursor.fetchall()
                    cursor.close()
                    return render_template('dashboard.html',items_data=items_data)
                else:
                    flash('no data found')
                    return redirect(url_for('index'))
            else:
                return redirect(url_for('index'))
        except Exception as e:
            print(e)
            flash('Cantfind anything')
            return redirect(url_for('userlogin'))
    else:
        return redirect(url_for('userlogin'))
    

app.run(debug=True,use_reloader=True)