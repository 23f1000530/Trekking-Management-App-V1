"""
Trekk Management App — Admin & Demo Data Seed Script

Pre-creates the Admin user programmatically using SQLAlchemy ORM, then seeds
realistic demo data (staff, trekkers, treks, assignments, bookings) so a fresh
clone has meaningful dashboards.

Idempotent: every insert is guarded by an existence check (username, trek name,
or user+trek pair), so running this script any number of times never duplicates
data.

Usage:
    python seed_admin.py
"""

from datetime import date, datetime, timedelta, timezone

from app import create_app, db
from app.models.user import User
from app.models.staff_profile import StaffProfile
from app.models.trek import Trek
from app.models.trek_assignment import TrekAssignment
from app.models.booking import Booking
from config import Config

# Demo credentials (all demo accounts share these passwords)
STAFF_PASSWORD = 'staff123'
TREKKER_PASSWORD = 'trek123'

TODAY = date.today()
NOW = datetime.now(timezone.utc)


def seed_admin():
    """Create the default Admin user if it doesn't already exist."""
    # Check if admin already exists
    existing_admin = User.query.filter_by(role='admin').first()

    if existing_admin:
        print(f'[OK] Admin user already exists: {existing_admin.username} ({existing_admin.email})')
        return

    # Create the admin user
    admin = User(
        username=Config.ADMIN_USERNAME,
        email=Config.ADMIN_EMAIL,
        role='admin',
        is_active=True,
        is_approved=True,
    )
    admin.set_password(Config.ADMIN_PASSWORD)

    db.session.add(admin)
    db.session.commit()

    print('=' * 50)
    print('[SUCCESS] Admin user created successfully!')
    print('=' * 50)
    print(f'   Username : {Config.ADMIN_USERNAME}')
    print(f'   Email    : {Config.ADMIN_EMAIL}')
    print(f'   Password : {Config.ADMIN_PASSWORD}')
    print(f'   Role     : admin')
    print('=' * 50)
    print('[WARNING] Change the default password in production!')
    print('=' * 50)


# ── Demo data definitions ──────────────────────────────────────────────

STAFF = [
    {
        'username': 'rahul_guide', 'email': 'rahul@trekk.com',
        'full_name': 'Rahul Sharma', 'phone': '+91-98100-11223',
        'experience_years': 8, 'specialization': 'High altitude treks',
    },
    {
        'username': 'meera_trails', 'email': 'meera@trekk.com',
        'full_name': 'Meera Nair', 'phone': '+91-98450-44556',
        'experience_years': 5, 'specialization': 'Forest & valley treks',
    },
]

TREKKERS = [
    {'username': 'arjun_k', 'email': 'arjun@example.com'},
    {'username': 'priya_v', 'email': 'priya@example.com'},
    {'username': 'dev_hikes', 'email': 'dev@example.com'},
]

TREKS = [
    {
        'name': 'Triund Ridge Trek',
        'location': 'McLeod Ganj, Himachal Pradesh',
        'difficulty': 'easy', 'status': 'open',
        'duration_days': 2, 'max_slots': 20, 'price': 2500.0,
        'start_date': TODAY + timedelta(days=20),
        'description': 'A gentle weekend climb to the Triund ridge with sweeping '
                       'views of the Dhauladhar range. Ideal first Himalayan trek.',
    },
    {
        'name': 'Valley of Flowers Expedition',
        'location': 'Chamoli, Uttarakhand',
        'difficulty': 'moderate', 'status': 'open',
        'duration_days': 6, 'max_slots': 16, 'price': 9500.0,
        'start_date': TODAY + timedelta(days=35),
        'description': 'Walk through a UNESCO World Heritage valley carpeted with '
                       'alpine flowers in full monsoon bloom.',
    },
    {
        'name': 'Hampta Pass Crossing',
        'location': 'Manali, Himachal Pradesh',
        'difficulty': 'moderate', 'status': 'ongoing',
        'duration_days': 5, 'max_slots': 12, 'price': 12000.0,
        'start_date': TODAY - timedelta(days=2),
        'description': 'A dramatic crossover trek from the lush Kullu valley to the '
                       'stark desert of Lahaul, currently underway.',
    },
    {
        'name': 'Kedarkantha Summit',
        'location': 'Sankri, Uttarakhand',
        'difficulty': 'hard', 'status': 'completed',
        'duration_days': 6, 'max_slots': 15, 'price': 11500.0,
        'start_date': TODAY - timedelta(days=26),
        'completion_notes': 'All participants summited in clear weather. '
                            'No incidents reported.',
        'description': 'A classic winter summit climb through pine forests and '
                       'snowfields to a 12,500 ft peak.',
    },
    {
        'name': 'Chadar Frozen River Trek',
        'location': 'Leh, Ladakh',
        'difficulty': 'extreme', 'status': 'approved',
        'duration_days': 9, 'max_slots': 10, 'price': 24000.0,
        'start_date': TODAY + timedelta(days=75),
        'description': 'Walk the frozen Zanskar river in deep winter. Approved and '
                       'awaiting publication for booking.',
    },
    {
        'name': 'Rajmachi Fort Trail',
        'location': 'Lonavala, Maharashtra',
        'difficulty': 'easy', 'status': 'pending',
        'duration_days': 2, 'max_slots': 30, 'price': 1800.0,
        'start_date': TODAY + timedelta(days=50),
        'description': 'A monsoon fort trek through the Sahyadris with waterfalls '
                       'en route. Awaiting admin review.',
    },
]

# staff username -> trek names (unique constraint on trek+staff prevents dupes,
# but we still check before inserting)
ASSIGNMENTS = {
    'rahul_guide': ['Hampta Pass Crossing', 'Kedarkantha Summit', 'Chadar Frozen River Trek'],
    'meera_trails': ['Triund Ridge Trek', 'Valley of Flowers Expedition', 'Hampta Pass Crossing'],
}

# (trekker username, trek name) -> booking details
BOOKINGS = [
    {'user': 'arjun_k', 'trek': 'Triund Ridge Trek',
     'status': 'confirmed', 'payment': 'paid', 'participants': 2},
    {'user': 'priya_v', 'trek': 'Triund Ridge Trek',
     'status': 'pending', 'payment': 'unpaid', 'participants': 1},
    {'user': 'priya_v', 'trek': 'Valley of Flowers Expedition',
     'status': 'confirmed', 'payment': 'paid', 'participants': 1},
    {'user': 'arjun_k', 'trek': 'Hampta Pass Crossing',
     'status': 'confirmed', 'payment': 'paid', 'participants': 1},
    {'user': 'dev_hikes', 'trek': 'Hampta Pass Crossing',
     'status': 'confirmed', 'payment': 'paid', 'participants': 2},
    {'user': 'dev_hikes', 'trek': 'Kedarkantha Summit',
     'status': 'completed', 'payment': 'paid', 'participants': 1},
    {'user': 'priya_v', 'trek': 'Kedarkantha Summit',
     'status': 'cancelled', 'payment': 'refunded', 'participants': 1},
]


def get_or_create_user(username, email, role, password, approved=True):
    """Return the user with this username, creating it if missing."""
    user = User.query.filter_by(username=username).first()
    if user:
        print(f'[OK]  User already exists: {username} ({user.role})')
        return user, False

    user = User(username=username, email=email, role=role,
                is_active=True, is_approved=approved)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # get user.id for dependent rows
    print(f'[ADD] User: {username} ({role})')
    return user, True


def seed_demo_data():
    """Seed staff, trekkers, treks, assignments and bookings (idempotent)."""

    # ── Trek staff (approved) with profiles ────────────────────────────
    for spec in STAFF:
        user, created = get_or_create_user(
            spec['username'], spec['email'], 'trek_staff', STAFF_PASSWORD
        )
        if created or not StaffProfile.query.filter_by(user_id=user.id).first():
            db.session.add(StaffProfile(
                user_id=user.id,
                full_name=spec['full_name'],
                phone=spec['phone'],
                experience_years=spec['experience_years'],
                specialization=spec['specialization'],
            ))
            print(f'[ADD]   Staff profile: {spec["full_name"]}')

    # ── Trekkers ───────────────────────────────────────────────────────
    for spec in TREKKERS:
        get_or_create_user(spec['username'], spec['email'], 'trekker', TREKKER_PASSWORD)

    # ── Treks ──────────────────────────────────────────────────────────
    for spec in TREKS:
        if Trek.query.filter_by(name=spec['name']).first():
            print(f'[OK]  Trek already exists: {spec["name"]}')
            continue

        start = spec['start_date']
        trek = Trek(
            name=spec['name'],
            description=spec['description'],
            difficulty=spec['difficulty'],
            duration_days=spec['duration_days'],
            max_slots=spec['max_slots'],
            available_slots=spec['max_slots'],
            price=spec['price'],
            location=spec['location'],
            start_date=start,
            end_date=start + timedelta(days=spec['duration_days'] - 1),
            status=spec['status'],
        )
        # Lifecycle timestamps consistent with the status
        if spec['status'] in ('approved', 'open', 'closed', 'ongoing', 'completed'):
            trek.approved_at = NOW - timedelta(days=40)
        if spec['status'] == 'completed':
            trek.completed_at = NOW - timedelta(days=20)
            trek.completion_notes = spec.get('completion_notes')
        db.session.add(trek)
        print(f'[ADD] Trek: {spec["name"]} ({spec["status"]}, {spec["difficulty"]})')

    db.session.flush()

    # ── Staff assignments ──────────────────────────────────────────────
    for username, trek_names in ASSIGNMENTS.items():
        staff = User.query.filter_by(username=username).first()
        for trek_name in trek_names:
            trek = Trek.query.filter_by(name=trek_name).first()
            if not staff or not trek:
                continue
            if TrekAssignment.query.filter_by(trek_id=trek.id, staff_id=staff.id).first():
                print(f'[OK]  Assignment exists: {username} -> {trek_name}')
                continue
            db.session.add(TrekAssignment(trek_id=trek.id, staff_id=staff.id, is_active=True))
            print(f'[ADD] Assignment: {username} -> {trek_name}')

    # ── Bookings ───────────────────────────────────────────────────────
    for spec in BOOKINGS:
        user = User.query.filter_by(username=spec['user']).first()
        trek = Trek.query.filter_by(name=spec['trek']).first()
        if not user or not trek:
            continue
        if Booking.query.filter_by(user_id=user.id, trek_id=trek.id).first():
            print(f'[OK]  Booking exists: {spec["user"]} -> {spec["trek"]}')
            continue

        participants = spec['participants']
        booking = Booking(
            user_id=user.id,
            trek_id=trek.id,
            booking_status=spec['status'],
            payment_status=spec['payment'],
            number_of_participants=participants,
            total_amount=trek.price * participants,
            booking_date=NOW - timedelta(days=10),
        )
        if spec['status'] == 'completed':
            booking.completed_at = trek.completed_at or NOW
        if spec['status'] == 'cancelled':
            booking.cancelled_at = NOW - timedelta(days=25)

        # Slots are held by active and fulfilled bookings; cancelled ones
        # released theirs.
        if spec['status'] in ('pending', 'confirmed', 'completed'):
            trek.book_slot(participants)

        db.session.add(booking)
        print(f'[ADD] Booking: {spec["user"]} -> {spec["trek"]} '
              f'({spec["status"]}, {participants} pax)')

    db.session.commit()

    print('=' * 50)
    print('[SUCCESS] Demo data seeded.')
    print('=' * 50)
    print(f'   Staff    : rahul_guide / meera_trails (password: {STAFF_PASSWORD})')
    print(f'   Trekkers : arjun_k / priya_v / dev_hikes (password: {TREKKER_PASSWORD})')
    print('=' * 50)


def seed():
    """Run all seeding steps inside one app context."""
    app = create_app()

    with app.app_context():
        # Create all tables (in case migrations haven't been run)
        db.create_all()

        seed_admin()
        seed_demo_data()


if __name__ == '__main__':
    seed()
