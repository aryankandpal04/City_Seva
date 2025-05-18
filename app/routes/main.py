from flask import Blueprint, render_template, flash, redirect, url_for
from app.forms.contact import ContactForm
from app.utils.email import send_contact_email

main = Blueprint('main', __name__, template_folder='templates')

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/about')
def about():
    return render_template('about.html')

@main.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        try:
            # Send email notification
            send_contact_email(form.name.data, form.email.data, form.subject.data, form.message.data)
            flash('Thank you for your message! We will get back to you soon.', 'success')
            return redirect(url_for('main.contact'))
        except Exception as e:
            flash('Sorry, there was an error sending your message. Please try again later.', 'danger')
    return render_template('contact.html', form=form) 