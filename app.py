from flask import Flask, render_template, redirect, url_for, flash, request
from flask_mysqldb import MySQL
from config import Config
from forms import RegisterForm, LoginForm, BookingForm, BookingDateForm, AddCarForm
from flask_bcrypt import Bcrypt 
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from datetime import datetime

# ----------- APP CONFIG ----------- #
app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ----------- HELPER FUNCTIONS ----------- #
def get_all_cars():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM cars")
    cars = cur.fetchall()
    cur.close()
    return cars

def get_user_rentals(customer_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT r.id, c.model, c.license_plate, c.status, r.rent_date, r.return_date, c.id
        FROM rentals r
        JOIN cars c ON r.car_id = c.id
        WHERE r.customer_id = %s
        ORDER BY r.rent_date DESC
    """, (customer_id,))
    rentals = cur.fetchall()
    cur.close()
    return rentals

# ----------- USER LOADER ----------- #
class User(UserMixin):
    def __init__(self, id, email, role):
        self.id = id
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, email, role FROM customers WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    if user:
        return User(id=user[0], email=user[1], role=user[2])
    return None

# ----------- ROUTES ----------- #

# Home Page (Public)
@app.route('/')
def home():
    return render_template('home.html')

# Dashboard (After login)
@app.route('/dashboard')
@login_required
def dashboard():
    cars = get_all_cars()
    rentals = get_user_rentals(current_user.id)
    return render_template('index.html', cars=cars, rentals=rentals)

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO customers (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        mysql.connection.commit()
        cur.close()

        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password_input = form.password.data

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, password, role FROM customers WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user[1], password_input):
            user_obj = User(id=user[0], email=email, role=user[2])
            login_user(user_obj)
            flash('Login successful!', 'success')
            if user_obj.role == 'admin':
                return redirect(url_for('admin_cars'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Import these at the top if not already
from datetime import datetime

# Book Car Route
@app.route('/book/<int:car_id>', methods=['GET', 'POST'])
@login_required
def book_car(car_id):
    form = BookingDateForm()

    if form.validate_on_submit():
        name = form.customer_name.data
        phone = form.phone.data
        license_num = form.license_number.data
        bank = form.bank_details.data
        pickup = form.pickup_location.data
        dropoff = form.dropoff_location.data
        start = form.start_date.data
        end = form.end_date.data

        days = (end - start).days
        rate_per_day = 50  # Set your per-day rental rate
        total_cost = days * rate_per_day

        if days <= 0:
            flash("End date must be after start date!", "danger")
            return redirect(request.url)

        cur = mysql.connection.cursor()

        # Insert booking into rentals table
        cur.execute("""
            INSERT INTO rentals (customer_id, car_id, rent_date, return_date, customer_name, phone, license_number, bank_details, pickup_location, dropoff_location)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (current_user.id, car_id, start, end, name, phone, license_num, bank, pickup, dropoff))
        
        rental_id = cur.lastrowid  # Get the rental ID for payment reference

        # Insert payment into payments table
        cur.execute("""
            INSERT INTO payments (customer_id, rental_id, amount_paid, payment_method, payment_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (current_user.id, rental_id, total_cost, "Bank Transfer", datetime.now()))

        # Update car status to 'Rented'
        cur.execute("UPDATE cars SET status = 'Rented' WHERE id = %s", (car_id,))

        mysql.connection.commit()
        cur.close()

        # Fetch car model and license_plate for confirmation page
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, model, license_plate FROM cars WHERE id = %s", (car_id,))
        car = cur.fetchone()
        cur.close()

        # Prepare booking details tuple
        booking = (rental_id, car[1], car[2], start, end)

        # Show the booking confirmation page with booking details
        return render_template('booking_confirmation.html', booking=booking, days=days, total_cost=total_cost)

    # If method is GET, render the booking form
    return render_template('book_form.html', form=form, car_id=car_id)

# Return Car
@app.route('/return/<int:rental_id>/<int:car_id>', methods=['POST'])
@login_required
def return_car(rental_id, car_id):
    cur = mysql.connection.cursor()

    # Update car status back to Available
    cur.execute("UPDATE cars SET status = 'Available' WHERE id = %s", (car_id,))

    # Update return_date to NOW
    cur.execute("UPDATE rentals SET return_date = %s WHERE id = %s", (datetime.now(), rental_id))

    mysql.connection.commit()
    cur.close()

    flash('Car returned successfully!', 'success')
    return redirect(url_for('dashboard'))

# Admin Login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password_input = form.password.data

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, password, role FROM customers WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user[1], password_input):
            if user[2] == 'admin':
                user_obj = User(id=user[0], email=email, role=user[2])
                login_user(user_obj)
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin_cars'))
            else:
                flash('Access denied. Not an admin account.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('admin_login.html', form=form)

# Admin - View Cars
@app.route('/admin/cars')
@login_required
def admin_cars():
    if current_user.role != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, model, license_plate, status FROM cars")
    cars = cur.fetchall()
    cur.close()

    return render_template('admin_cars.html', cars=cars)

# Admin - Add Car
@app.route('/admin/add_car', methods=['GET', 'POST'])
@login_required
def add_car():
    if current_user.role != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('home'))

    form = AddCarForm()
    if form.validate_on_submit():
        model = form.model.data
        plate = form.license_plate.data

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO cars (model, license_plate, status) VALUES (%s, %s, %s)", (model, plate, 'Available'))
        mysql.connection.commit()
        cur.close()

        flash('Car added successfully!', 'success')
        return redirect(url_for('admin_cars'))

    return render_template('add_car.html', form=form)

# Admin - Delete Car
@app.route('/admin/delete_car/<int:car_id>', methods=['POST'])
@login_required
def delete_car(car_id):
    if current_user.role != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM cars WHERE id = %s", (car_id,))
    mysql.connection.commit()
    cur.close()

    flash('Car deleted successfully!', 'success')
    return redirect(url_for('admin_cars'))

# Admin - View All Rentals
@app.route('/admin/rentals')
@login_required
def admin_rentals():
    if current_user.role != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT r.id, cu.name, cu.email, c.model, c.license_plate, r.rent_date, r.return_date
        FROM rentals r
        JOIN customers cu ON r.customer_id = cu.id
        JOIN cars c ON r.car_id = c.id
        ORDER BY r.rent_date DESC
    """)
    all_rentals = cur.fetchall()
    cur.close()

    return render_template('admin_rentals.html', rentals=all_rentals)
@app.route('/mark_unavailable/<int:car_id>', methods=['POST'])
@login_required
def mark_unavailable(car_id):
    if current_user.role != 'admin':
        flash('Unauthorized Access', 'danger')
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    cur.execute("UPDATE cars SET status = 'Not Available' WHERE id = %s", (car_id,))
    mysql.connection.commit()
    cur.close()

    flash('Car marked as Not Available', 'success')
    return redirect(url_for('manage_cars'))


# ----------- RUN THE APP ----------- #
if __name__ == '__main__':
    print("🚀 Starting Flask app on http://127.0.0.1:5000/")
    app.run(debug=True)
