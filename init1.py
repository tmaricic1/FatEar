#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect, flash
from datetime import datetime
import hashlib
from passlib.hash import sha256_crypt
import pymysql.cursors

#for uploading photo:
from app import app
#from flask import Flask, flash, request, redirect, render_template
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

##get the date
date = datetime.now()

###Initialize the app from Flask
app = Flask(__name__)
app.secret_key = "secret key"

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 8889,
                       user='root',
                       password='root',
                       db='FatEar',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)


def allowed_image(filename):

    if not "." in filename:
        return False

    ext = filename.rsplit(".", 1)[1]

    if ext.upper() in app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        return True
    else:
        return False


def allowed_image_filesize(filesize):

    if int(filesize) <= app.config["MAX_IMAGE_FILESIZE"]:
        return True
    else:
        return False


#Define a route to hello function
@app.route('/')
def hello():
    return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    return render_template('register.html')

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password']

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM user WHERE username = %s'
    cursor.execute(query, username)
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if(data):
        cursor = conn.cursor()
        query = 'SELECT password FROM user WHERE username = %s'
        cursor.execute(query, username)
        result = cursor.fetchone()
        db_password = result['password']
        cursor.close()
        salt = "salt"
        verify_password = salt+password
        if sha256_crypt.verify(verify_password, db_password):
             session['username'] = username
             return redirect(url_for('home'))
        else:
            error = 'Invalid password'
            return render_template('login.html', error=error)
    else:
        #returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password']
    fname = request.form['fname']
    lname = request.form['lname']
    nickname = request.form['nickname']

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM user WHERE username = %s'
    cursor.execute(query, (username))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO user VALUES(%s, %s, %s, %s, %s, %s)'
        salt = "salt"
        salted_password = salt+password
        encrypted_password = sha256_crypt.hash(salted_password)
        cursor.execute(ins, (username, encrypted_password, fname, lname, date.strftime("%Y/%m/%d"), nickname))
        conn.commit()
        cursor.close()
        return render_template('index.html')


@app.route('/home')
def home():
    user = session['username']
    cursor = conn.cursor()
    query = 'SELECT lastlogin FROM user WHERE username = %s'
    cursor.execute(query, user)
    date = cursor.fetchone()
    cursor.close()
    cursor = conn.cursor()
    query = 'SELECT title, reviewText, username FROM (reviewSong NATURAL JOIN song) NATURAL JOIN (SELECT DISTINCT username FROM (SELECT * FROM (SELECT user1 AS username FROM friend WHERE user2 = %s AND acceptStatus = "Accepted") AS t1 UNION (SELECT user2 AS username FROM friend WHERE user1 = %s AND acceptStatus = "Accepted")) AS s1 UNION (SELECT follows as username FROM follows WHERE follower = %s)) as r1 WHERE reviewDate >= %s'
    cursor.execute(query, (user, user, user, date['lastlogin'].strftime('%Y-%m-%d')))
    data = cursor.fetchall()
    cursor.close()

    cursor = conn.cursor()
    query = 'SELECT title, fname, lname, releaseDate FROM (SELECT artistID FROM userFanOfArtist WHERE username = %s) as t1 NATURAL JOIN artistPerformsSong NATURAL JOIN song NATURAL JOIN artist WHERE releaseDate >= %s'
    cursor.execute(query, (user, date['lastlogin'].strftime('%Y-%m-%d')))
    data2 = cursor.fetchall()

    #might want to confirm password in the below query
    date = datetime.now()
    cursor = conn.cursor()
    ins = 'UPDATE user SET lastlogin = %s WHERE username = %s'
    cursor.execute(ins, (date.strftime("%Y/%m/%d"), user))
    conn.commit()

    cursor.close()
    return render_template('home.html', user = user, reviews = data, songs = data2) 


@app.route('/search')
def search():
    return render_template('search.html')   

@app.route('/friends')
def friends():
    user = session['username']
    cursor = conn.cursor()
    query = ' SELECT user1 FROM (SELECT user1, user2 FROM friend WHERE (user1 = %s or user2 = %s) and acceptStatus = "accepted") as friend_pairs WHERE user1 != %s UNION (SELECT user2 FROM (SELECT user1, user2 FROM friend WHERE (user1 = %s or user2 = %s) and acceptStatus = "accepted") as friend_pairs WHERE user2 != %s)'
    cursor.execute(query, (user, user, user, user, user, user))
    data = cursor.fetchall()

    query = 'SELECT user1 FROM (SELECT user1, user2 FROM friend WHERE (user1 = %s or user2 = %s) and requestSentBy != %s and acceptStatus = "Pending") AS friend_pairs WHERE user1 != %s UNION (SELECT user2 FROM (SELECT user1, user2 FROM friend WHERE (user1 = %s or user2 = %s) and requestSentBy != %s and acceptStatus = "Pending") AS friend_pairs WHERE user2 != %s)'
    cursor.execute(query, (user, user, user, user, user, user, user, user))
    pend = cursor.fetchall()

    query = 'SELECT user1 FROM (SELECT user1, user2 FROM friend WHERE (user1 = %s or user2 = %s) and requestSentBy = %s and acceptStatus = "Pending") AS friend_pairs WHERE user1 != %s UNION (SELECT user2 FROM (SELECT user1, user2 FROM friend WHERE (user1 = %s or user2 = %s) and requestSentBy = %s and acceptStatus = "Pending") AS friend_pairs WHERE user2 != %s)'
    cursor.execute(query, (user, user, user, user, user, user, user, user))
    unaccepted = cursor.fetchall()

    cursor.close()
    return render_template('friends.html', friends = data, pend = pend, unaccepted = unaccepted, user = user)

@app.route('/accept/<user1>/<user2>')
def acceptFriend(user1, user2):
    cursor = conn.cursor()
    update = 'UPDATE friend SET acceptStatus = "Accepted", updatedAt = CURRENT_TIME()  WHERE (user1 = %s and user2 = %s) or (user1 = %s and user2 = %s);'
    cursor.execute(update, (user1, user2, user2, user1))
    cursor.close()
    return redirect("/friends", code=302)

@app.route('/decline/<user1>/<user2>')
def declineFriend(user1, user2):
    cursor = conn.cursor()
    update = 'UPDATE friend SET acceptStatus = "Not accepted", updatedAt = CURRENT_TIME()  WHERE (user1 = %s and user2 = %s) or (user1 = %s and user2 = %s);'
    cursor.execute(update, (user1, user2, user2, user1))
    cursor.close()
    return redirect("/friends", code=302)


@app.route('/addFriendSearch', methods=['GET', 'POST'])
def addFriendSearch():
    user = session["username"]
    fuser = request.form['username']
    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM user WHERE username = %s'
    cursor.execute(query, fuser)
    exists = cursor.fetchone()
    if not exists:
        flash("User does not exist")
        return redirect('/friends', code = 302)
    else:
        query = 'SELECT * FROM friend WHERE (user1 = %s AND user2 = %s) OR (user1 = %s AND user2 = %s) AND acceptStatus = "Accepted"'
        cursor.execute(query, (user, fuser, fuser, user))
    #stores the results in a variable
        data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
        if(data):
        #If the previous query returns data, then playlist Name already exists
            flash("You are already friends with this user")
            return redirect('/friends', code = 302)
        else:
            query = 'SELECT * FROM friend WHERE (user1 = %s AND user2 = %s) OR (user1 = %s AND user2 = %s)'
            cursor.execute(query, (user, fuser, fuser, user))
    #stores the results in a variable
            prevInt = cursor.fetchone()
            if(prevInt):
                update = 'UPDATE friend SET acceptStatus = "Pending", updatedAt = CURRENT_TIME()  WHERE (user1 = %s and user2 = %s) or (user1 = %s and user2 = %s);'
                cursor.execute(update, (user, fuser, fuser, user))
            else:
                insert = 'INSERT INTO friend VALUES (%s, %s, "Pending", %s, CURRENT_TIME(), NULL)'
                cursor.execute(insert, (user, fuser, user))
    conn.commit()
    cursor.close()
    return redirect('/friends', code=302)

@app.route('/followers')
def followers():
    user = session['username']
    cursor = conn.cursor()
    query = ' SELECT follower FROM follows WHERE follows = %s'
    cursor.execute(query, (user))
    pplWhoFollowYou = cursor.fetchall()

    query = ' SELECT follows FROM follows WHERE follower = %s'
    cursor.execute(query, (user))
    pplWhoYouFollow = cursor.fetchall()

    cursor.close()
    return render_template('followers.html', pplWhoFollowYou = pplWhoFollowYou, pplWhoYouFollow = pplWhoYouFollow, user = user)

@app.route('/followSearch', methods=['GET', 'POST'])
def followSearch():
    user = session["username"]
    fuser = request.form['username']
    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM user WHERE username = %s'
    cursor.execute(query, fuser)
    exists = cursor.fetchone()
    if not exists:
        flash("User does not exist")
        return redirect('/followers', code = 302)
    else:
        query = 'SELECT * FROM follows WHERE follower = %s AND follows = %s'
        cursor.execute(query, (user, fuser))
    #stores the results in a variable
        data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
        if(data):
        #If the previous query returns data, then playlist Name already exists
            flash("You already follow this user")
            return redirect('/followers', code = 302)
        else:
                insert = 'INSERT INTO follows VALUES (%s, %s, CURRENT_TIME())'
                cursor.execute(insert, (user, fuser))
    conn.commit()
    cursor.close()
    return redirect('/followers', code=302)


@app.route('/byArtist')
def byArtist():
    return render_template('byArtist.html')

@app.route('/showArtist', methods=['GET', 'POST'])
def showArtist():
    name = request.form['info']
    cursor = conn.cursor()
    fullname = name.split()
    if len(fullname) == 1:
        fname = fullname[0]
        query = 'SELECT title, fname, lname, albumTitle, songURL FROM (song NATURAL JOIN songInAlbum NATURAL JOIN album) NATURAL JOIN artistPerformsSong NATURAL JOIN artist  WHERE fname = %s'
        cursor.execute(query, fname)
        data = cursor.fetchall()
    else:
        fname = fullname[0]
        lname = fullname[1]
        query = 'SELECT title, fname, lname, albumTitle, songURL FROM (song NATURAL JOIN songInAlbum NATURAL JOIN album) NATURAL JOIN artistPerformsSong NATURAL JOIN artist WHERE fname = %s AND lname = %s'
        cursor.execute(query, (fname, lname))
        data = cursor.fetchall()
    cursor.close()
    return render_template('showArtist.html', name = name, names = data)

@app.route('/byRating')
def byRating():
    return render_template('byRating.html')  

@app.route('/showRating', methods=['GET', 'POST'])
def showRating():
    stars = request.form['info']
    cursor = conn.cursor()
    query = 'SELECT title, fname, lname, albumTitle, songURL FROM ((song NATURAL JOIN songInAlbum NATURAL JOIN album) NATURAL JOIN artistPerformsSong NATURAL JOIN artist) JOIN rateSong USING (songID)  WHERE stars = %s'
    cursor.execute(query, int(stars))
    data = cursor.fetchall()
    print(data)
    cursor.close()
    return render_template('showRating.html', stars = stars, results = data)

@app.route('/byGenre')
def byGenre():
    return render_template('byGenre.html')             

@app.route('/showGenre', methods=['GET', 'POST'])
def showGenre():
    genre = request.form['info']
    cursor = conn.cursor()
    query = 'SELECT title, fname, lname, albumTitle, songURL FROM ((song NATURAL JOIN songInAlbum NATURAL JOIN album) NATURAL JOIN artistPerformsSong NATURAL JOIN artist) JOIN songGenre USING (songID)  WHERE genre = %s'
    cursor.execute(query, genre)
    data = cursor.fetchall()
    cursor.close()
    return render_template('showGenre.html', genre = genre, results = data)

@app.route('/post', methods=['GET', 'POST'])
def post():
    username = session['username']
    cursor = conn.cursor();
    blog = request.form['blog']
    query = 'INSERT INTO blog (blog_post, username) VALUES(%s, %s)'
    cursor.execute(query, (blog, username))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))

@app.route('/select_blogger')
def select_blogger():
    #check that user is logged in
    username = session['username']
    #should throw exception if username not found
    
    cursor = conn.cursor();
    query = 'SELECT DISTINCT username FROM blog'
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return render_template('select_blogger.html', user_list=data)

@app.route('/show_posts', methods=["GET", "POST"])
def show_posts():
    poster = request.args['poster']
    cursor = conn.cursor();
    query = 'SELECT ts, blog_post FROM blog WHERE username = %s ORDER BY ts DESC'
    cursor.execute(query, poster)
    data = cursor.fetchall()
    cursor.close()
    return render_template('show_posts.html', poster_name=poster, posts=data)

@app.route('/searchMusic', methods=['GET', 'POST'])
def searchMusic():
    name = request.form['info']
    searchType = request.args['searchType']
    if searchType == 'Artist':
        cursor = conn.cursor()
        fullname = name.split()
        fname = fullname[0]
        lname = fullname[1]
        query = 'SELECT fname,lname FROM artist WHERE fname LIKE %s OR lname LIKE %s'
        cursor.execute(query, (fname, lname))
        data = cursor.fetchall()
        return render_template('search.html', searchType, results = data)


def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
	
@app.route('/')
def upload_form():
	return render_template('upload.html')

@app.route('/', methods=['POST'])
def upload_file():
	if request.method == 'POST':
        # check if the post request has the file part
		if 'file' not in request.files:
			flash('No file part')
			return redirect(request.url)
		file = request.files['file']
		if file.filename == '':
			flash('No file selected for uploading')
			return redirect(request.url)
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			flash('File successfully uploaded')
			return redirect('/')
		else:
			flash('Allowed file types are txt, pdf, png, jpg, jpeg, gif')
			return redirect(request.url)

@app.route('/playlist', methods=['GET', 'POST'])
def user_playlists():
    # Retrieve the playlists for the specified user from the database
    username = session["username"]
    cursor = conn.cursor()
    query = "SELECT distinct pName,description FROM playlist WHERE username = %s"
    cursor.execute(query, username)
    playlists = cursor.fetchall()
    cursor.close()

    # Render the "playlists.html" template with the retrieved playlists
    return render_template('playlist.html', playlists=playlists)

@app.route('/playlistdisplay', methods=['GET', 'POST'])
def playlistdisplay():
    # Retrieve the songs on the specified playlist for the specified user from the database
    cursor = conn.cursor()
    playlist = request.form["plist"]
    query = 'SELECT pname FROM playlist WHERE pname = %s'
    cursor.execute(query, playlist)
    pname = cursor.fetchone()
    query = "SELECT song.title FROM songInPlaylist NATURAL JOIN song WHERE pName = %s"
    cursor.execute(query, playlist)
    songs = cursor.fetchall()
    cursor.close()
    print(pname['pname'])
    return render_template('playlistdisplay.html',songs = songs)

@app.route('/playlistcreate', methods=['GET', 'POST'])
def playlistcreate():
    username = session["username"]
    pname = request.form['pname']
    description = request.form['description']
    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM `Playlist` WHERE pName = %s AND username = %s'
    cursor.execute(query, (pname, username))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then playlist Name already exists
        error = "This playlist name already exists"
        return render_template('playlistcreate.html', error = error)
    else:
        ins = 'INSERT INTO `Playlist` (`pName`, `username`, `description`, `dateCreated`) VALUES(%s, %s,%s,%s)'
        cursor.execute(ins, (pname,username,description, date.strftime("%Y/%m/%d"),))
        conn.commit()
        cursor.close()
    return redirect('/playlist')

@app.route('/playlistaddsong')
def playlistaddsong():
    return render_template('playlistaddsong.html')

@app.route('/playlistaddsongSearch', methods=['GET', 'POST'])
def playlistaddsongSearch():
    username = session["username"]
    pname = request.form['pname']
    sname = request.form['sname']
    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM songInPlaylist NATURAL JOIN song WHERE title = %s AND pName = %s'
    cursor.execute(query, (sname, pname))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then playlist Name already exists
        error = "This song is already on this playlist"
        return render_template('playlistaddsong.html', error = error)
    else:
        songidq = 'SELECT songID FROM `song` WHERE title = %s'
        cursor.execute(songidq,(sname))
        songid = cursor.fetchone()
        ins = 'INSERT INTO `songInPlaylist` (`pName`, `songID`, `username`) VALUES (%s, %s, %s)'
        print(songid)
        print(pname)
        print(username)
        cursor.execute(ins, (pname,songid['songID'],username))
        conn.commit()
        cursor.close()
    return redirect('/playlist')
    
@app.route('/playlistcreatepage')
def playlistcreatepage():
    return render_template('playlistcreate.html')
@app.route('/rateReview')
def rateReview():
    return render_template('rateReview.html')
@app.route('/rateSong')
def rateSong():
    return render_template('rateSong.html')
@app.route('/reviewSong')
def reviewSong():
    return render_template('reviewSong.html')
@app.route('/postRating', methods = ['GET', 'POST'])
def postRating():
     username = session["username"]
     title = request.form['songTitle']
     rating = request.form['songRating']
     if int(rating) < 0 or int(rating) > 5:
          error = 'invalid rating'
          return render_template('rateSong.html', error = error)
     date = datetime.now()
     cursor = conn.cursor()
     query = 'SELECT songID FROM song WHERE title = %s'
     cursor.execute(query, title)
     songID = cursor.fetchone()
     if not songID:
        error = "No song with this name"
        return render_template('rateSong.html', error = error)
     query = 'SELECT * FROM rateSong WHERE songID = %s and username = %s'
     cursor.execute(query, (songID['songID'], username))
     entry = cursor.fetchone()
     if (entry):
        error = 'You already rated this song'
        return render_template('reviewSong.html', error = error)
     elif(songID):
        ins = 'INSERT INTO rateSong VALUES (%s, %s, %s, %s)'
        cursor.execute(ins, (username, songID['songID'], rating, date.strftime("%Y/%m/%d")))
        conn.commit()

     cursor.close()
     return redirect('/home')
@app.route('/postReview', methods = ['GET', 'POST'])
def postReview():
     username = session["username"]
     title = request.form['songTitle']
     review = request.form['songReview']
     date = datetime.now()
     cursor = conn.cursor()
     query = 'SELECT songID FROM song WHERE title = %s'
     cursor.execute(query, title)
     songID = cursor.fetchone()
     if not songID:
        error = "No song with this name"
        return render_template('rateSong.html', error = error)
     query = 'SELECT * FROM reviewSong WHERE songID = %s and username = %s'
     cursor.execute(query, (songID['songID'], username))
     entry = cursor.fetchone()
     if (entry):
        error = 'You already reviewed this song'
        return render_template('reviewSong.html', error = error)
     elif (songID):
        ins = 'INSERT INTO reviewSong VALUES (%s, %s, %s, %s)'
        cursor.execute(ins, (username, songID['songID'], review, date.strftime("%Y/%m/%d")))
        conn.commit()

     cursor.close()
     return redirect('/home')


@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')
        
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
