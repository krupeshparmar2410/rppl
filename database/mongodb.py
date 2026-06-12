"""
=============================================================================
  AI TRANSFORMER HEALTH MONITORING SYSTEM — MongoDB Connection & CRUD Utility
  RPPL Transformers · normalized collection design
=============================================================================
"""

import os
import sys
import time
import datetime
import math
from bson import ObjectId
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Import centralized logger
from utils.logger import get_logger

logger = get_logger("mongodb")

# Retrieve MongoDB URI from environment variables
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "transformer_monitoring"

# Global PyMongo variables
client = None
db = None
transformers_col = None
history_col = None

# Predefined transformer master metadata
MASTER_TRANSFORMERS = [
    {
        "transformer_id": "TR001",
        "transformer_name": "Ahmedabad Transformer 1",
        "city": "Ahmedabad",
        "service_station": "Ahmedabad Service Center",
        "latitude": 23.0225,
        "longitude": 72.5714,
        "installation_date": "2023-01-15T00:00:00",
        "capacity_kva": 100,
        "status": "Active"
    },
    {
        "transformer_id": "TR002",
        "transformer_name": "Surat Transformer 2",
        "city": "Surat",
        "service_station": "Surat Service Center",
        "latitude": 21.1702,
        "longitude": 72.8311,
        "installation_date": "2023-05-20T00:00:00",
        "capacity_kva": 150,
        "status": "Active"
    },
    {
        "transformer_id": "TR003",
        "transformer_name": "Vadodara Transformer 3",
        "city": "Vadodara",
        "service_station": "Vadodara Service Center",
        "latitude": 22.3072,
        "longitude": 73.1812,
        "installation_date": "2023-08-10T00:00:00",
        "capacity_kva": 200,
        "status": "Active"
    },
    {
        "transformer_id": "TR004",
        "transformer_name": "Rajkot Transformer 4",
        "city": "Rajkot",
        "service_station": "Rajkot Service Center",
        "latitude": 22.3039,
        "longitude": 70.8022,
        "installation_date": "2023-11-05T00:00:00",
        "capacity_kva": 250,
        "status": "Active"
    }
]

def create_indexes():
    """Creates single-field and compound indexes automatically on startup."""
    try:
        logger.info("Initializing database indexes...")
        
        # Unique index on transformers master table
        transformers_col.create_index("transformer_id", unique=True)
        
        # Single-field indexes on history/telemetry table
        history_col.create_index("transformer_id")
        history_col.create_index("created_at")
        history_col.create_index("predicted_health")
        history_col.create_index("maintenance_status")
        history_col.create_index("fault_priority")
        history_col.create_index("alert_sent")
        
        # Compound index for optimized lookup queries
        history_col.create_index([("transformer_id", 1), ("created_at", -1)])
        
        logger.info("Database indexes created/verified successfully.")
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")

def seed_database():
    """Seeds the transformers master collection if it is empty or legacy schema is detected."""
    try:
        # Check if legacy schema exists (no 'city' field in existing docs)
        has_legacy = False
        if transformers_col.count_documents({}) > 0:
            sample = transformers_col.find_one()
            if sample and "city" not in sample:
                has_legacy = True
                
        if has_legacy:
            logger.info("Legacy transformers collection detected. Re-creating for new schema...")
            transformers_col.drop()
            
        if transformers_col.count_documents({}) == 0:
            transformers_col.insert_many(MASTER_TRANSFORMERS)
            logger.info("Master transformers collection seeded successfully.")
        else:
            logger.info("Master transformers collection already seeded.")
    except Exception as e:
        logger.error(f"Error seeding transformers: {e}")

def initialize_database():
    """
    Initializes MongoClient and handles connection timeouts, connection retries, 
    and auto-indexing on boot.
    """
    global client, db, transformers_col, history_col
    
    # Configure hardened connect options:
    # serverSelectionTimeoutMS, connectTimeoutMS, and socketTimeoutMS are all set to 5000ms
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000
    )
    db = client[DB_NAME]
    transformers_col = db["transformers"]
    history_col = db["transformer_history"]
    
    max_attempts = 3
    retry_wait_seconds = 2
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Connecting to MongoDB Atlas (Attempt {attempt}/{max_attempts})...")
            # Trigger connection attempt by executing a ping command
            client.admin.command('ping')
            logger.info("Connected successfully to MongoDB Atlas.")
            
            # Successfully connected; build indexes and seed database
            create_indexes()
            seed_database()
            return
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"MongoDB connection attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                time.sleep(retry_wait_seconds)
            else:
                logger.critical("Failed to connect to MongoDB Atlas after 3 attempts. Exiting application gracefully.")
                sys.exit(1)
        except Exception as e:
            logger.critical(f"Unexpected error initializing MongoDB connection: {e}. Exiting.")
            sys.exit(1)

# Invoke connection setup on module import
initialize_database()

def calculate_nearest_service_station(lat, lon):
    """
    Calculates the nearest service station using the Haversine formula.
    Returns (station_name, distance_km)
    """
    if lat is None or lon is None:
        return "Ahmedabad Service Center", 0.0
        
    stations = [
        {"name": "Ahmedabad Service Center", "latitude": 23.0225, "longitude": 72.5714},
        {"name": "Surat Service Center", "latitude": 21.1702, "longitude": 72.8311},
        {"name": "Vadodara Service Center", "latitude": 22.3072, "longitude": 73.1812},
        {"name": "Rajkot Service Center", "latitude": 22.3039, "longitude": 70.8022}
    ]
    
    min_dist = float('inf')
    nearest_station = None
    
    R = 6371.0 # Earth's radius in km
    
    for station in stations:
        try:
            lat1 = math.radians(float(lat))
            lon1 = math.radians(float(lon))
            lat2 = math.radians(station["latitude"])
            lon2 = math.radians(station["longitude"])
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            dist = R * c
            
            if dist < min_dist:
                min_dist = dist
                nearest_station = station["name"]
        except Exception:
            continue
            
    if nearest_station is None:
        return "Ahmedabad Service Center", 0.0
        
    return nearest_station, round(min_dist, 2)

def insert_prediction(record):
    """
    Inserts a new telemetry/prediction document into transformer_history.
    Automatically flags fault_detected_time if status is Warning/Critical.
    """
    try:
        now = datetime.datetime.now()
        # Parse DeviceTimeStamp if it is string
        ts = record.get("DeviceTimeStamp")
        if isinstance(ts, str):
            try:
                # support standard ISO parsing
                ts_dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                ts_dt = now
        else:
            ts_dt = ts or now

        # Add created_at
        record["created_at"] = now
        # Format DeviceTimeStamp for uniformity
        record["DeviceTimeStamp"] = ts_dt.isoformat() if isinstance(ts_dt, datetime.datetime) else str(ts_dt)

        # Fault tracking
        is_fault = record.get("predicted_health") in ["Warning", "Critical"]
        if is_fault:
            record["fault_detected_time"] = now
        else:
            record["fault_detected_time"] = None

        # Nearest Service Station Calculation
        transformer_id = record.get("transformer_id")
        lat = None
        lon = None
        if transformer_id:
            try:
                t_metadata = transformers_col.find_one({"transformer_id": transformer_id})
                if t_metadata:
                    lat = t_metadata.get("latitude")
                    lon = t_metadata.get("longitude")
            except Exception as e:
                logger.error(f"Failed to lookup coordinates for nearest station: {e}")
                
        if lat is None or lon is None:
            lat = record.get("latitude") or 23.0225
            lon = record.get("longitude") or 72.5714

        station_name, distance = calculate_nearest_service_station(lat, lon)
        record["nearest_service_station"] = station_name
        record["distance_km"] = distance

        # SLA Configuration based on Fault Priority
        priority = record.get("fault_priority") or "P4"
        sla_targets = {
            "P1": 15,
            "P2": 30,
            "P3": 120,      # 2 hours
            "P4": 1440      # 24 hours
        }
        record["sla_target_minutes"] = sla_targets.get(priority, 1440)
        record["sla_breached"] = False

        # Additional Workflow Fields
        record["maintenance_status"] = record.get("maintenance_status") or "Pending"
        record["acknowledged_time"] = None
        record["assigned_time"] = None
        record["in_progress_time"] = None
        record["resolved_time"] = None
        
        record["response_time_minutes"] = None
        record["repair_time_minutes"] = None
        
        record["assigned_engineer"] = None
        record["engineer_email"] = None
        record["engineer_phone"] = None
        
        record["reopen_count"] = 0
        record["reopen_reason"] = None
        record["reopened_time"] = None
        
        record["resolution_notes"] = None
        record["resolved_by"] = None

        # Fault Status Audit Timeline
        record["status_history"] = [
            {
                "status": record["maintenance_status"],
                "timestamp": now,
                "updated_by": "System"
            }
        ]

        result = history_col.insert_one(record)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Error inserting prediction: {e}")
        return None

def update_maintenance_status(record_id, status, assigned_engineer=None, 
                              engineer_email=None, engineer_phone=None, 
                              reopen_reason=None, resolution_notes=None, 
                              resolved_by=None, updated_by="Technician"):
    """
    Updates the maintenance workflow status of a history record.
    Allowed values: Pending, Acknowledged, Assigned, In Progress, Resolved, Reopened.
    Calculates response_time_minutes and repair_time_minutes appropriately.
    """
    try:
        now = datetime.datetime.now()
        doc = history_col.find_one({"_id": ObjectId(record_id)})
        if not doc:
            return False

        update_fields = {"maintenance_status": status}
        
        # Pull or inherit fault detected time
        fault_detected = doc.get("fault_detected_time")
        if not fault_detected:
            # Fallback to created_at or current time
            fault_detected = doc.get("created_at") or now

        # SLA settings helper
        sla_target = doc.get("sla_target_minutes") or 1440

        if status == "Acknowledged":
            update_fields["acknowledged_time"] = now
            # response time = acknowledged_time - fault_detected_time
            dt_diff = (now - fault_detected).total_seconds() / 60.0
            update_fields["response_time_minutes"] = round(dt_diff, 1)
            update_fields["sla_breached"] = dt_diff > sla_target

        elif status == "Assigned":
            update_fields["assigned_time"] = now
            if assigned_engineer is not None:
                update_fields["assigned_engineer"] = assigned_engineer
            if engineer_email is not None:
                update_fields["engineer_email"] = engineer_email
            if engineer_phone is not None:
                update_fields["engineer_phone"] = engineer_phone

        elif status == "In Progress":
            update_fields["in_progress_time"] = now

        elif status == "Resolved":
            # Set resolved_time
            update_fields["resolved_time"] = now
            
            # If it wasn't acknowledged, write acknowledged_time as well
            if not doc.get("acknowledged_time"):
                update_fields["acknowledged_time"] = now
                dt_diff_resp = (now - fault_detected).total_seconds() / 60.0
                update_fields["response_time_minutes"] = round(dt_diff_resp, 1)
                update_fields["sla_breached"] = dt_diff_resp > sla_target
                
            # If not assigned or in progress, write them as well
            if not doc.get("assigned_time"):
                update_fields["assigned_time"] = now
            if not doc.get("in_progress_time"):
                update_fields["in_progress_time"] = now

            if resolution_notes is not None:
                update_fields["resolution_notes"] = resolution_notes
            if resolved_by is not None:
                update_fields["resolved_by"] = resolved_by
                
            # repair time = resolved_time - fault_detected_time (corrected total duration since detection)
            dt_diff_repair = (now - fault_detected).total_seconds() / 60.0
            update_fields["repair_time_minutes"] = round(dt_diff_repair, 1)

        elif status == "Reopened":
            update_fields["reopened_time"] = now
            update_fields["reopen_count"] = (doc.get("reopen_count") or 0) + 1
            if reopen_reason is not None:
                update_fields["reopen_reason"] = reopen_reason
                
            # Clear resolution fields
            update_fields["resolved_time"] = None
            update_fields["repair_time_minutes"] = None
            update_fields["resolution_notes"] = None
            update_fields["resolved_by"] = None

        # Build status audit entry
        audit_entry = {
            "status": status,
            "timestamp": now,
            "updated_by": updated_by or "Technician"
        }

        history_col.update_one(
            {"_id": ObjectId(record_id)}, 
            {
                "$set": update_fields,
                "$push": {"status_history": audit_entry}
            }
        )
        return True
    except Exception as e:
        logger.error(f"Error updating maintenance status: {e}")
        return False

def update_alert_sent(record_id, status=True):
    """Updates the alert_sent status and timestamp of a prediction document."""
    try:
        now = datetime.datetime.now()
        update_fields = {"alert_sent": status}
        if status:
            update_fields["alert_timestamp"] = now
        else:
            update_fields["alert_timestamp"] = None
            
        history_col.update_one(
            {"_id": ObjectId(record_id)}, 
            {"$set": update_fields}
        )
        return True
    except Exception as e:
        logger.error(f"Error updating alert_sent status: {e}")
        return False

def get_last_alert_time(transformer_id):
    """
    Retrieves the timestamp of the latest record for this transformer where alert_sent is True.
    Used for 30-minute cooldown checking.
    """
    try:
        latest = history_col.find_one(
            {"transformer_id": transformer_id, "alert_sent": True},
            sort=[("created_at", DESCENDING)]
        )
        if latest:
            return latest.get("created_at")
        return None
    except Exception as e:
        logger.error(f"Error checking last alert time: {e}")
        return None

def get_history(search=None, sort_by="timestamp_desc", filter_health=None, 
                filter_maintenance=None, filter_severity=None, filter_priority=None, 
                page=1, per_page=10):
    """
    Retrieves historical records with lookup joins, search, filters, sorting, and pagination.
    """
    try:
        # Build aggregation pipeline
        pipeline = [
            {
                "$lookup": {
                    "from": "transformers",
                    "localField": "transformer_id",
                    "foreignField": "transformer_id",
                    "as": "transformer"
                }
            },
            {
                "$unwind": {
                    "path": "$transformer",
                    "preserveNullAndEmptyArrays": True
                }
            }
        ]

        # Match (Filter) Stage
        match_conditions = {}
        if filter_health:
            match_conditions["predicted_health"] = filter_health
        if filter_maintenance:
            match_conditions["maintenance_status"] = filter_maintenance
        if filter_severity:
            match_conditions["fault_severity"] = filter_severity
        if filter_priority:
            match_conditions["fault_priority"] = filter_priority

        if search:
            match_conditions["$or"] = [
                {"transformer_id": {"$regex": search, "$options": "i"}},
                {"fault_type": {"$regex": search, "$options": "i"}},
                {"transformer.city": {"$regex": search, "$options": "i"}},
                {"transformer.location": {"$regex": search, "$options": "i"}},
                {"transformer.service_station": {"$regex": search, "$options": "i"}},
                {"fault_priority": {"$regex": search, "$options": "i"}}
            ]

        if match_conditions:
            pipeline.append({"$match": match_conditions})

        # Count total matches before pagination
        count_pipeline = pipeline + [{"$count": "total"}]
        count_result = list(history_col.aggregate(count_pipeline))
        total_records = count_result[0]["total"] if count_result else 0

        # Custom Severity Rank calculation
        if sort_by == "severity_desc":
            pipeline.append({
                "$addFields": {
                    "severity_rank": {
                        "$switch": {
                            "branches": [
                                {"case": {"$eq": ["$fault_severity", "Critical"]}, "then": 4},
                                {"case": {"$eq": ["$fault_severity", "High"]}, "then": 3},
                                {"case": {"$eq": ["$fault_severity", "Medium"]}, "then": 2},
                                {"case": {"$eq": ["$fault_severity", "Low"]}, "then": 1}
                            ],
                            "default": 0
                        }
                    }
                }
            })

        # Sort Stage
        sort_dict = {}
        if sort_by == "timestamp_desc":
            sort_dict["created_at"] = -1
        elif sort_by == "timestamp_asc":
            sort_dict["created_at"] = 1
        elif sort_by == "health_desc":
            sort_dict["health_score"] = -1
        elif sort_by == "health_asc":
            sort_dict["health_score"] = 1
        elif sort_by == "priority_asc":
            sort_dict["fault_priority"] = 1  # P1, P2...
        elif sort_by == "severity_desc":
            sort_dict["severity_rank"] = -1
        else:
            sort_dict["created_at"] = -1

        pipeline.append({"$sort": sort_dict})

        # Pagination Stage
        skip_val = (page - 1) * per_page
        pipeline.append({"$skip": skip_val})
        pipeline.append({"$limit": per_page})

        records = list(history_col.aggregate(pipeline))

        # Format ObjectIds and datetimes for JSON
        for r in records:
            r["_id"] = str(r["_id"])
            if "transformer" in r and r["transformer"]:
                r["city"] = r["transformer"].get("city")
                r["location"] = r["transformer"].get("city") or r["transformer"].get("location")
                r["service_station"] = r["transformer"].get("service_station")
                r["latitude"] = r["transformer"].get("latitude")
                r["longitude"] = r["transformer"].get("longitude")
                r["transformer_name"] = r["transformer"].get("transformer_name")
                r["capacity_kva"] = r["transformer"].get("capacity_kva")
            else:
                # fallback values
                r["city"] = r.get("city") or r.get("location", "Unknown")
                r["location"] = r["city"]
                r["service_station"] = r.get("service_station", "Unknown")
                r["latitude"] = r.get("latitude", 0.0)
                r["longitude"] = r.get("longitude", 0.0)
                r["transformer_name"] = r.get("transformer_name", "Unknown")
                r["capacity_kva"] = r.get("capacity_kva", 0)

            # Convert datetime fields to ISO strings for serializability
            date_fields = ["created_at", "fault_detected_time", "acknowledged_time", 
                           "assigned_time", "in_progress_time", "resolved_time", 
                           "reopened_time", "alert_timestamp"]
            for df in date_fields:
                val = r.get(df)
                if isinstance(val, datetime.datetime):
                    r[df] = val.isoformat()

            # Format status_history timestamps
            if "status_history" in r and isinstance(r["status_history"], list):
                for entry in r["status_history"]:
                    ts = entry.get("timestamp")
                    if isinstance(ts, datetime.datetime):
                        entry["timestamp"] = ts.isoformat()

        return records, total_records
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return [], 0

def get_dashboard_stats():
    """
    Computes dashboard counts, averages, and active repair metrics using aggregation pipelines.
    """
    try:
        total = history_col.count_documents({})
        healthy = history_col.count_documents({"predicted_health": "Healthy"})
        warning = history_col.count_documents({"predicted_health": "Warning"})
        critical = history_col.count_documents({"predicted_health": "Critical"})
        emails_sent = history_col.count_documents({"alert_sent": True})
        pending_repairs = history_col.count_documents({"maintenance_status": "Pending"})
        resolved_repairs = history_col.count_documents({"maintenance_status": "Resolved"})
        
        p1_faults = history_col.count_documents({"fault_priority": "P1"})
        p2_faults = history_col.count_documents({"fault_priority": "P2"})

        # Phase 2 KPI updates
        total_faults = history_col.count_documents({"predicted_health": {"$in": ["Warning", "Critical"]}})
        active_faults = history_col.count_documents({
            "predicted_health": {"$in": ["Warning", "Critical"]},
            "maintenance_status": {"$ne": "Resolved"}
        })

        # SLA compliance percentage calculation
        responded_faults = history_col.count_documents({
            "fault_priority": {"$in": ["P1", "P2", "P3"]},
            "response_time_minutes": {"$ne": None}
        })
        breached_faults = history_col.count_documents({
            "fault_priority": {"$in": ["P1", "P2", "P3"]},
            "sla_breached": True
        })
        
        sla_compliance = 100.0
        if responded_faults > 0:
            sla_compliance = round(((responded_faults - breached_faults) / responded_faults) * 100, 1)

        sla_breached_count = history_col.count_documents({"sla_breached": True})

        # Average health score
        avg_health = 100.0
        health_pipeline = [{"$group": {"_id": None, "avg_health": {"$avg": "$health_score"}}}]
        health_res = list(history_col.aggregate(health_pipeline))
        if health_res and health_res[0]["avg_health"] is not None:
            avg_health = round(health_res[0]["avg_health"], 1)

        # Average Response Time (minutes)
        avg_response = 0.0
        resp_pipeline = [{"$match": {"response_time_minutes": {"$ne": None}}}, 
                         {"$group": {"_id": None, "avg_resp": {"$avg": "$response_time_minutes"}}}]
        resp_res = list(history_col.aggregate(resp_pipeline))
        if resp_res and resp_res[0]["avg_resp"] is not None:
            avg_response = round(resp_res[0]["avg_resp"], 1)

        # Average Repair Time (minutes)
        avg_repair = 0.0
        repair_pipeline = [{"$match": {"repair_time_minutes": {"$ne": None}}}, 
                           {"$group": {"_id": None, "avg_rep": {"$avg": "$repair_time_minutes"}}}]
        repair_res = list(history_col.aggregate(repair_pipeline))
        if repair_res and repair_res[0]["avg_rep"] is not None:
            avg_repair = round(repair_res[0]["avg_rep"], 1)

        # Transformers Requiring Maintenance
        pipeline_req = [
            {"$sort": {"created_at": -1}},
            {
                "$group": {
                    "_id": "$transformer_id",
                    "latest_health": {"$first": "$predicted_health"},
                    "latest_maintenance": {"$first": "$maintenance_status"}
                }
            },
            {
                "$match": {
                    "$or": [
                        {"latest_health": {"$ne": "Healthy"}},
                        {"latest_maintenance": {"$ne": "Resolved"}}
                    ]
                }
            },
            {"$count": "count"}
        ]
        req_res = list(history_col.aggregate(pipeline_req))
        requiring_maintenance = req_res[0]["count"] if req_res else 0

        # Active Critical Faults (predicted_health is Critical, maintenance_status is not Resolved)
        active_critical = history_col.count_documents({
            "predicted_health": "Critical",
            "maintenance_status": {"$ne": "Resolved"}
        })

        return {
            "total_processed": total,
            "healthy_count": healthy,
            "warning_count": warning,
            "critical_count": critical,
            "emails_sent": emails_sent,
            "pending_repairs": pending_repairs,
            "resolved_repairs": resolved_repairs,
            "avg_health_score": avg_health,
            "active_critical_faults": active_critical,
            "transformers_requiring_maintenance": requiring_maintenance,
            "p1_emergency_faults": p1_faults,
            "p2_high_priority_faults": p2_faults,
            "avg_response_time": avg_response,
            "avg_repair_time": avg_repair,
            "total_faults": total_faults,
            "active_faults": active_faults,
            "sla_compliance": sla_compliance,
            "sla_breached_count": sla_breached_count
        }
    except Exception as e:
        logger.error(f"Error computing dashboard stats: {e}")
        return {}

def get_analytics_data():
    """
    Computes analytics groupings including City, Service Station, Priorities, and Trends.
    """
    try:
        # 1. Fault Count by City
        city_pipeline = [
            {"$match": {"predicted_health": {"$ne": "Healthy"}}},
            {
                "$lookup": {
                    "from": "transformers",
                    "localField": "transformer_id",
                    "foreignField": "transformer_id",
                    "as": "transformer"
                }
            },
            {"$unwind": "$transformer"},
            {"$group": {"_id": "$transformer.city", "count": {"$sum": 1}}},
            {"$project": {"city": "$_id", "count": 1, "_id": 0}}
        ]
        city_faults = list(history_col.aggregate(city_pipeline))

        # 2. Fault Count by Service Station
        station_pipeline = [
            {"$match": {"predicted_health": {"$ne": "Healthy"}}},
            {
                "$lookup": {
                    "from": "transformers",
                    "localField": "transformer_id",
                    "foreignField": "transformer_id",
                    "as": "transformer"
                }
            },
            {"$unwind": "$transformer"},
            {"$group": {"_id": "$transformer.service_station", "count": {"$sum": 1}}},
            {"$project": {"service_station": "$_id", "count": 1, "_id": 0}}
        ]
        station_faults = list(history_col.aggregate(station_pipeline))

        # 3. Priority Distribution
        priority_pipeline = [
            {"$group": {"_id": "$fault_priority", "count": {"$sum": 1}}},
            {"$project": {"priority": "$_id", "count": 1, "_id": 0}}
        ]
        priority_dist = list(history_col.aggregate(priority_pipeline))

        # 4. Maintenance Status Distribution
        status_pipeline = [
            {"$group": {"_id": "$maintenance_status", "count": {"$sum": 1}}},
            {"$project": {"status": "$_id", "count": 1, "_id": 0}}
        ]
        status_dist = list(history_col.aggregate(status_pipeline))

        # 5. Daily Fault Trend (number of warning/critical occurrences per day)
        daily_pipeline = [
            {"$match": {"predicted_health": {"$ne": "Healthy"}}},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}},
            {"$project": {"date": "$_id", "count": 1, "_id": 0}}
        ]
        daily_trends = list(history_col.aggregate(daily_pipeline))

        # 6. Monthly Fault Trend
        monthly_pipeline = [
            {"$match": {"predicted_health": {"$ne": "Healthy"}}},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m", "date": "$created_at"}},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}},
            {"$project": {"month": "$_id", "count": 1, "_id": 0}}
        ]
        monthly_trends = list(history_col.aggregate(monthly_pipeline))

        # 7. Fault Type Distribution
        fault_type_pipeline = [
            {"$match": {"predicted_health": {"$ne": "Healthy"}}},
            {"$group": {"_id": "$fault_type", "count": {"$sum": 1}}},
            {"$project": {"fault_type": "$_id", "count": 1, "_id": 0}}
        ]
        fault_types = list(history_col.aggregate(fault_type_pipeline))

        return {
            "city_faults": city_faults,
            "station_faults": station_faults,
            "priority_distribution": priority_dist,
            "maintenance_status_distribution": status_dist,
            "daily_trends": daily_trends,
            "monthly_trends": monthly_trends,
            "fault_type_distribution": fault_types
        }
    except Exception as e:
        logger.error(f"Error generating analytics: {e}")
        return {}

def get_transformer_health_timeline(transformer_id):
    """
    Returns the history timeline of health scores, status, and fault types for a specific transformer.
    """
    try:
        records = list(history_col.find(
            {"transformer_id": transformer_id},
            {"DeviceTimeStamp": 1, "health_score": 1, "predicted_health": 1, "fault_type": 1},
            sort=[("created_at", 1)]
        ))
        for r in records:
            r["_id"] = str(r["_id"])
        return records
    except Exception as e:
        logger.error(f"Error fetching health timeline: {e}")
        return []
