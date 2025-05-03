from flask import Blueprint, request
from src.database.api.services import attendance_service
from src.utils.jwt_helper import admin_required, login_required

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')


@attendance_bp.route('/mark', methods=['POST'])
@admin_required
def mark_attendance():
    data = request.get_json()
    meeting_id = data.get('meeting_id')
    student_id = data.get('student_id')
    scan_type = data.get('scan_type')  # "in" atau "out"

    if not all([meeting_id, student_id, scan_type]):
        return {"message": "All fields are required."}, 400

    attendance, error = attendance_service.mark_attendance(
        meeting_id, student_id, scan_type)
    if error:
        return {"message": error}, 400

    return {
        "message": "Attendance recorded successfully.",
        "attendance": {
            "id": attendance.id,
            "check_in_time": attendance.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if attendance.check_in_time else None,
            "check_out_time": attendance.check_out_time.strftime('%Y-%m-%d %H:%M:%S') if attendance.check_out_time else None,
            "status": attendance.status
        }
    }, 200


@attendance_bp.route('/by-meeting/<int:meeting_id>', methods=['GET'])
@login_required
def get_attendance_by_meeting(meeting_id):
    attendances = attendance_service.get_attendance_by_meeting(meeting_id)

    attendance_list = [{
        "student_id": a.class_student.student_id,  # << akses lewat relasi
        "check_in_time": a.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if a.check_in_time else None,
        "check_out_time": a.check_out_time.strftime('%Y-%m-%d %H:%M:%S') if a.check_out_time else None,
        "status": a.status
    } for a in attendances]

    return {"attendances": attendance_list}, 200


@attendance_bp.route('/scan', methods=['POST'])
@admin_required  # atau login_required, tergantung siapa yang scan
def scan_hand_for_attendance():
    if 'file' not in request.files:
        return {"message": "No file uploaded."}, 400

    file = request.files['file']
    meeting_id = request.form.get('meeting_id')
    scan_type = request.form.get('scan_type')  # "in" atau "out"

    if not all([meeting_id, scan_type]):
        return {"message": "Meeting ID and scan type are required."}, 400

    # Save uploaded file temporarily
    temp_path = f"/tmp/{file.filename}"
    file.save(temp_path)

    # Import predict function
    from src.utils.hand_recognition import predict_student_id

    # Predict student_id using the CNN model
    student_id = predict_student_id(temp_path)

    if not student_id:
        return {"message": "Hand not recognized."}, 400

    # Now reuse your existing attendance marking service
    attendance, error = attendance_service.mark_attendance(
        meeting_id=int(meeting_id),
        student_id=student_id,
        scan_type=scan_type
    )

    if error:
        return {"message": error}, 400

    return {
        "message": "Attendance marked successfully.",
        "attendance": {
            "id": attendance.id,
            "check_in_time": attendance.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if attendance.check_in_time else None,
            "check_out_time": attendance.check_out_time.strftime('%Y-%m-%d %H:%M:%S') if attendance.check_out_time else None,
            "status": attendance.status
        }
    }, 200
