import json
import asyncio
import httpx
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sys
import time
import os

# Global set to track expired attendances
expired_attendances = set()

async def get_sid(email: str, password: str):
    """Login to Bennett ERP and retrieve session ID"""
    login_url = "https://student.bennetterp.camu.in/login/validate"
    payload = {
        "dtype": "M",
        "Email": email,
        "pwd": password
    }
    
    print(f"[AUTH] Attempting login for {email}...")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(login_url, json=payload)
            data = response.json()["output"]["data"]
            session_id = response.cookies.get("connect.sid")

            if "logindetails" in data:
                print(f"[AUTH] Login successful! Got session ID: {session_id[:10]}...")
                return session_id
            else:
                print(f"[AUTH] Login failed for {email}")
                return None
    except Exception as e:
        print(f"[AUTH] Error during login: {e}")
        return None

async def mark_attendance(session_id: str, attendance_id: str, student_id: str):
    url = "https://student.bennetterp.camu.in/api/Attendance/record-online-attendance"
    headers = {
        "Cookie": f"connect.sid={session_id}",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, /",
        "Content-Type": "application/json",
        "Origin": "https://student.bennetterp.camu.in",
        "Referer": "https://student.bennetterp.camu.in/v2/timetable",
    }
    payload = {
        "attendanceId": attendance_id,
        "isMeetingStarted": True,
        "StuID": student_id,
        "offQrCdEnbld": True,
        "latitude": "28.4518",  # Bennett University approximate coordinates
        "longitude": "77.5737",
        "accuracy": "10"
    }

    try:
        print(f"\n[SENDING] Marking attendance request for ID: {attendance_id}")
        print(f"[REQUEST] URL: {url}")
        print(f"[REQUEST] Payload: {json.dumps(payload, indent=2)}")
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.post(url, headers=headers, json=payload)
            elapsed = time.time() - start_time
            
            print(f"[RESPONSE] Status Code: {response.status_code} (took {elapsed:.2f}s)")
            print(f"[RESPONSE] Text: {response.text}")
            
            data = response.json()
            print(f"[RESPONSE] JSON: {json.dumps(data, indent=2)}")
            
            if data.get("output", {}).get("data") is not None:
                code = data["output"]["data"]["code"]
                if code in ["SUCCESS", "ATTENDANCE_ALREADY_RECORDED"]:
                    return True
                elif code == "ATTENDANCE_NOT_VALID":
                    print(f"[INFO] Attendance not valid yet - meeting might not be active")
                    return False
                else:
                    print(f"[INFO] Unexpected response code: {code}")
            return False
    except Exception as e:
        print(f"[ERROR] While marking for student {student_id}: {e}")
        return False

async def fetch_timetable(sid, student_id, target_date=None):
    """Fetch timetable using the session ID"""
    api_url = "https://student.bennetterp.camu.in/api/Timetable/get"
    
    cookies = {
        "connect.sid": sid
    }
    
    if target_date is None:
        target_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    
    json_payload = {
        "PrName": "Undergraduate",
        "SemID": "6674080baa6e1fcb4aedb235",
        "SemName": "Semester - 5",
        "AcYrNm": "2025-2026",
        "AcyrToDt": "2026-06-30",
        "AcyrFrDt": "2025-07-01",
        "DeptCode": "SCSET",
        "DepName": "School of Computer Science Engineering & Technology",
        "CrCode": "B.Tech.(CSE)",
        "CrName": "Bachelor of Technology (Computer Science and Engineering)",
        "InName": "Bennett University",
        "CmProgID": "68862ad42fda3dbda69264ed",
        "_id": "68862ad42fda3dbda69264ed",
        "stustatus": "Progressed",
        "progstdt": "2025-07-27T13:34:12.793Z",
        "StuID": student_id,
        "semRstd": "6674080baa6e1fcb4aedb235",
        "AcYr": "669291a9e22fa158b82ea968",
        "DeptID": "666471d086b084b1cb33e4dc",
        "CrID": "666473aae88943d812522d92",
        "PrID": "6664712a86b084b1cb33e4b2",
        "InId": "663474b11dd0e9412a1f793f",
        "OID": "663474b11dd0e9412a1f793f",
        "__v": 0,
        "StFl": "A",
        "MoAt": "2025-07-27T13:34:12.795Z",
        "CrAt": "2025-07-27T13:34:12.795Z",
        "isFE": True,
        "BP": "N",
        "lang_code": "663474b11dd0e9412a1f793f",
        "studStsNm": "Active",
        "studSts": "A",
        "FNa": "KUNTI SRUJAN",
        "LNa": "TEJA",
        "AplnNum": "E23CSEU1838",
        "CnEmail": "E23CSEU1838@bennett.edu.in",
        "enableV2": True,
        "start": target_date,
        "end": target_date,
        "schdlTyp": "slctdSchdl",
        "isShowCancelledPeriod": True,
        "isFromTt": True
    }
    
    headers = {
        "authority": "student.bennetterp.camu.in",
        "accept": "application/json, text/plain, /",
        "appversion": "v2",
        "clienttzofst": "330",
        "content-type": "application/json",
        "origin": "https://student.bennetterp.camu.in",
        "referer": "https://student.bennetterp.camu.in/v2/timetable",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    }
    
    try:
        now = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%H:%M:%S")
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, cookies=cookies, json=json_payload, headers=headers)
        
        elapsed = time.time() - start_time
        print(f"\n[{now}] [RESPONSE] Timetable check completed in {elapsed:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('output', {}).get('data') is None:
                print("[RESPONSE] No timetable data found")
                return None
                
            days = result.get('output', {}).get('data', [])
            attendance_found = False
            
            for day in days:
                for period in day.get("Periods", []):
                    if "attendanceId" in period:
                        attendance_found = True
                        faculty_name = period.get("StaffNm", "Unknown Faculty")
                        subject_name = period.get("SubNa", "Unknown Subject")
                        attendance_status = "Already Submitted" if period.get("isAttendanceSaved", False) else "Not Submitted"
                        
                        print(f"[RESPONSE] Found attendanceId: {period['attendanceId']}")
                        print(f"[RESPONSE] Subject: {subject_name}")
                        print(f"[RESPONSE] Faculty: {faculty_name}")
                        print(f"[RESPONSE] Attendance Status: {attendance_status}")
                        print(f"[RESPONSE] Time: {period.get('FrTime', 'Unknown')}")
            
            if not attendance_found:
                print("[RESPONSE] No active attendance sessions found")
                
            return result
        else:
            print(f"[ERROR] Received status code {response.status_code}")
            print(f"[RESPONSE] Text: {response.text}")
            return None
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return None

async def check_and_mark_attendance(sid, email, password, student_id):

    print("Starting attendance checker...")
    print(f"Time now: {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')}")
    print("Waiting for an active attendance session...")
    
    marked_attendance_ids = set() 
    request_count = 0
    last_sid_refresh = datetime.now()
    

    if sid is None:
        print("[AUTH] No session ID provided. Obtaining one...")
        sid = await get_sid(email, password)
        if sid is None:
            print("[ERROR] Failed to get a session ID. Check your credentials.")
            return
    
    while True:
        try:

            if datetime.now() - last_sid_refresh > timedelta(minutes=30):
                print("[AUTH] Refreshing session ID...")
                new_sid = await get_sid(email, password)
                if new_sid:
                    sid = new_sid
                    last_sid_refresh = datetime.now()
                    print("[AUTH] Session refreshed successfully!")
                else:
                    print("[AUTH] Failed to refresh session, continuing with existing session")
            
            request_count += 1
            current_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
            
            print(f"\n[REQUEST #{request_count}] Checking for attendance at {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%H:%M:%S')}")
            
            start_time = time.time()
            timetable_data = await fetch_timetable(sid, student_id, current_date)
            elapsed = time.time() - start_time
            
            if elapsed > 1.0:
                print(f"[WARNING] Request took {elapsed:.2f}s which is longer than our 1s check interval")
            
            if timetable_data and timetable_data.get("output", {}).get("data"):
                days = timetable_data.get("output", {}).get("data", [])
                

                for day in days:
                    for period in day.get("Periods", []):
                        if ("attendanceId" in period and 
                            not period.get("isAttendanceSaved", False) and 
                            period["attendanceId"] not in marked_attendance_ids):
                            
                            attendance_id = period["attendanceId"]
                            subject_name = period.get("SubNa", "Unknown Subject")
                            faculty_name = period.get("StaffNm", "Unknown Faculty")
                            time_slot = f"{period.get('FrTime', 'Unknown')} - {period.get('end', 'Unknown').split('T')[1].split('+')[0].split(':')[0]}:{period.get('end', 'Unknown').split('T')[1].split('+')[0].split(':')[1]}"
                            
                            # Check if we've recently tried this attendance
                            current_time = datetime.now()
                            last_attempt_key = f"{attendance_id}_last_attempt"
                            
                            # Don't spam if we just tried within last 30 seconds
                            if hasattr(check_and_mark_attendance, last_attempt_key):
                                last_attempt = getattr(check_and_mark_attendance, last_attempt_key)
                                if (current_time - last_attempt).seconds < 30:
                                    continue
                            
                            print(f"\n[FOUND] ✨ Active attendance for {subject_name} ✨")
                            print(f"[INFO] Faculty: {faculty_name}")
                            print(f"[INFO] AttendanceID: {attendance_id}")
                            print(f"[INFO] Time: {time_slot}")
                            
                            success = await mark_attendance(sid, attendance_id, student_id)
                            
                            # Remember when we last tried this attendance
                            setattr(check_and_mark_attendance, last_attempt_key, current_time)
                            
                            if success:
                                print(f"[SUCCESS] Attendance marked successfully for {subject_name} with {faculty_name}!")
                                marked_attendance_ids.add(attendance_id)
                            else:
                                print(f"[FAILURE] Failed to mark attendance for {subject_name} - will retry in 30 seconds")
                
                for day in days:
                    for period in day.get("Periods", []):
                        if ("attendanceId" in period and 
                            period.get("isAttendanceSaved", False) and 
                            period["attendanceId"] not in marked_attendance_ids):
                            
                            attendance_id = period["attendanceId"]
                            subject_name = period.get("SubNa", "Unknown Subject")
                            faculty_name = period.get("StaffNm", "Unknown Faculty")
                            
                            print(f"\n[INFO] Attendance for {subject_name} with {faculty_name} was already submitted!")
                            marked_attendance_ids.add(attendance_id)

            request_time = time.time() - start_time
            wait_time = max(0, 1.0 - request_time) 
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
        except KeyboardInterrupt:
            print("\n[INFO] Stopping attendance checker...")
            break
        except Exception as e:
            print(f"[ERROR] Error during attendance check: {e}")
            await asyncio.sleep(1)  

async def main():
    student_id = "668c1a15b26adcc7e79eb354"

    # Get credentials from environment variables
    email = os.getenv("BENNETT_EMAIL", "E23CSEU1838@bennett.edu.in")
    password = os.getenv("BENNETT_PASSWORD", "JeGjnF2f")

    print(f"\nLogging in as: {email}")
    sid = await get_sid(email, password)

    if not sid:
        print("[ERROR] Failed to login. Exiting.")
        return

    print(f"Student ID: {student_id}")
    print("Session ID: " + sid[:10] + "..." + sid[-5:])
    print("Time Zone: Asia/Kolkata")
    print("Current Time: " + datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"))
    print("\nRunning continuous attendance checker (Press Ctrl+C to stop)")
    print("Checking for active attendance sessions every second...")       

    await check_and_mark_attendance(sid, email, password, student_id)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Program terminated by user.")
        sys.exit(0)
