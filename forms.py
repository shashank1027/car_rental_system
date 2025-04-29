from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from wtforms import SelectField, DateField, SubmitField
from datetime import datetime
from wtforms import StringField, DateField, SubmitField
from wtforms.validators import DataRequired, Length

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
class AddCarForm(FlaskForm):
    model = StringField('Car Model', validators=[DataRequired()])
    license_plate = StringField('License Plate', validators=[DataRequired()])
    submit = SubmitField('Add Car')   
class BookingForm(FlaskForm):
    car_id = SelectField('Select Car', coerce=int, validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Book Now') 
    


class BookingDateForm(FlaskForm):
    customer_name = StringField('Customer Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    license_number = StringField('Driving License Number', validators=[DataRequired()])
    bank_details = StringField('Bank Details (or UPI ID)', validators=[DataRequired()])
    pickup_location = StringField('Pickup Location', validators=[DataRequired()])
    dropoff_location = StringField('Drop-off Location', validators=[DataRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Confirm Booking')
