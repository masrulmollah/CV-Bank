# The Streamlit application for the CV Bank.
# This app allows users to create and publish their CV profiles,
# which are then stored in a shared Firestore database for others to view.

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json

# --- Firestore and Firebase Setup ---
# This block attempts to get the configuration from the Canvas environment.
# If it fails, it assumes local execution and tries to load a service account key file.

try:
    # Code for the Canvas environment
    appId = __app_id
    firebaseConfig = json.loads(__firebase_config)
    initial_auth_token = __initial_auth_token

except NameError:
    # Code for local execution
    appId = 'local-app-id'
    try:
        # Assumes 'serviceAccountKey.json' is in the same directory
        with open('serviceAccountKey.json') as json_file:
            firebaseConfig = json.load(json_file)
    except FileNotFoundError:
        firebaseConfig = None
    initial_auth_token = None

# --- Custom Firebase Initialization ---
# The standard `firebase_admin.initialize_app()` function expects a path to a credentials file.
# Since we are provided with the config as a dictionary, we need to handle this manually.

def initialize_firebase():
    """Initializes the Firebase Admin SDK if it hasn't been initialized already."""
    if not firebase_admin._apps and firebaseConfig:
        try:
            # We use a service account dictionary directly from the config.
            # This is a safe way to initialize Firebase without a file.
            cred = credentials.Certificate(firebaseConfig)
            firebase_admin.initialize_app(cred)
            st.info("Firebase initialized successfully.")
        except Exception as e:
            st.error(f"Error initializing Firebase: {e}")
            return None
    elif not firebaseConfig:
        st.error("Firebase configuration is missing. Cannot connect to the database.")
        return None
    return firestore.client()

def save_profile(db_client, profile_data, user_id, doc_id=None):
    """
    Saves a new CV profile or updates an existing one to the Firestore database.
    The data is stored in a public collection so everyone can access it.
    """
    if db_client is None:
        st.error("Database not connected. Cannot save profile.")
        return

    profile_data["user_id"] = user_id

    try:
        # Define the public collection path.
        collection_path = f"artifacts/{appId}/public/data/cv_profiles"
        cv_profiles_ref = db_client.collection(collection_path)

        if doc_id:
            # Update the existing document
            doc_ref = cv_profiles_ref.document(doc_id)
            doc_ref.update(profile_data)
            st.success("CV updated successfully!")
        else:
            # Add the new document to the collection.
            cv_profiles_ref.add(profile_data)
            st.success("CV published successfully!")
    except Exception as e:
        st.error(f"An error occurred while saving the profile: {e}")

def load_profiles(db_client):
    """
    Loads all CV profiles from the public Firestore database.
    """
    if db_client is None:
        st.error("Database not connected. Cannot load profiles.")
        return []

    try:
        # Define the public collection path.
        collection_path = f"artifacts/{appId}/public/data/cv_profiles"
        cv_profiles_ref = db_client.collection(collection_path)
        
        # Get all documents in the collection.
        docs = cv_profiles_ref.stream()
        profiles = [{"id": doc.id, **doc.to_dict()} for doc in docs]
        return profiles
    except Exception as e:
        st.error(f"An error occurred while loading profiles: {e}")
        return []

def display_profile(profile, user_id, is_admin, key_suffix=""):
    """Helper function to display a single profile and its edit button."""
    is_owner = (profile.get("user_id") == user_id)
    with st.expander(f"**{profile.get('name', 'Anonymous Profile')}**"):
        if profile.get("contact"):
            st.write(f"**Contact:** {profile['contact']}")
        if profile.get("experience"):
            st.write(f"**Experience:** {', '.join(profile['experience'])}")
        if profile.get("profession"):
            st.write(f"**Profession:** {', '.join(profile['profession'])}")
        if profile.get("expertise"):
            st.write(f"**Expertise:** {', '.join(profile['expertise'])}")
        if profile.get("summary"):
            st.write(f"**Summary:**")
            st.info(profile['summary'])
        if profile.get("experience_text"):
            st.write(f"**Work Experience:**")
            st.info(profile['experience_text'])
        if profile.get("education"):
            st.write(f"**Education:**")
            st.info(profile['education'])
        if profile.get("skills"):
            st.write(f"**Skills:**")
            st.info(profile['skills'])
        # New "Additional Information" block
        # This condition checks if the list exists AND is not empty
        if profile.get("additional_info"):
            st.write(f"**Additional Information:**")
            # The 'additional_info' field is now always a list, so this loop is safe.
            if isinstance(profile['additional_info'], list):
                for info in profile['additional_info']:
                    st.info(info)
            else:
                # Handle the case where it might still be a string from an older record.
                st.info(profile['additional_info'])
        
        # Show edit button only to owner or admin.
        # The key is made unique by combining the profile ID and a suffix.
        if is_owner or is_admin:
            if st.button(f"Edit Profile", key=f"{profile['id']}_{key_suffix}"):
                st.session_state.edit_mode = True
                st.session_state.profile_to_edit = profile
                st.rerun()

# --- Streamlit UI Layout ---

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(page_title="CV Bank", layout="wide")

    st.title("👨‍💼 The Community CV Bank")
    st.markdown("### Create and share your professional profile with everyone!")
    
    db = initialize_firebase()

    # --- Authentication (Placeholder) ---
    user_id = "admin_456"
    admin_id = "admin_456"
    is_admin = (user_id == admin_id)
    
    # Define options for new multi-select fields
    experience_options = ["5 Years", "10 Years", "15 Years", "20+ Years"]
    profession_options = ["Finance", "Marketing", "Supply Chain", "IT", "HR"]
    expertise_options = ["Data Analytics", "Leadership", "Python", "Project Management", "UI/UX"]

    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False
        st.session_state.profile_to_edit = {}
        st.session_state.additional_info_list = [""] # Initialize with one empty field
    
    if db:
        # --- Sidebar Layout ---
        with st.sidebar:
            if not st.session_state.edit_mode:
                st.header("Create Your Profile")
                st.markdown("Fill out the form to publish your CV.")
                with st.form("cv_form", clear_on_submit=True):
                    name = st.text_input("Full Name")
                    contact = st.text_input("Contact Information (Email/Phone)")
                    
                    # New grouping inputs
                    experience_select = st.multiselect("Experience", experience_options, default=None)
                    profession_select = st.multiselect("Profession", profession_options, default=None)
                    expertise_select = st.multiselect("Expertise", expertise_options, default=None)

                    summary = st.text_area("Professional Summary")
                    experience_text = st.text_area("Work Experience")
                    education = st.text_area("Education")
                    skills = st.text_area("Skills (e.g., Python, SQL, HTML)")
                    
                    # Dynamic "Additional Information" block
                    st.write("Additional Information (e.g., Achievements, Certifications)")
                    for i, info in enumerate(st.session_state.additional_info_list):
                        st.session_state.additional_info_list[i] = st.text_input(
                            f"Info {i+1}", 
                            value=info,
                            key=f"add_info_create_{i}",
                            label_visibility="collapsed"
                        )
                    if st.form_submit_button("Add another information block"):
                        st.session_state.additional_info_list.append("")
                        st.rerun()

                    submitted = st.form_submit_button("Publish CV")
                    if submitted:
                        # Clean up empty strings from the list
                        cleaned_additional_info = [item for item in st.session_state.additional_info_list if item.strip()]
                        if not any([name, contact, summary, experience_text, education, skills]) and not cleaned_additional_info:
                            st.warning("Please fill out at least one field to publish your CV.")
                        else:
                            profile_data = {
                                "name": name,
                                "contact": contact,
                                "summary": summary,
                                "experience": experience_select,
                                "profession": profession_select,
                                "expertise": expertise_select,
                                "experience_text": experience_text,
                                "education": education,
                                "skills": skills,
                                "additional_info": cleaned_additional_info
                            }
                            save_profile(db, profile_data, user_id)
                            st.session_state.additional_info_list = [""] # Reset for next profile
            else:
                st.header("Edit Profile")
                st.markdown("Update the fields for your selected profile.")
                profile = st.session_state.profile_to_edit
                with st.form("edit_form", clear_on_submit=False):
                    name = st.text_input("Full Name", value=profile.get("name", ""))
                    contact = st.text_input("Contact Information (Email/Phone)", value=profile.get("contact", ""))
                    
                    experience_select = st.multiselect("Experience", experience_options, default=profile.get("experience", []))
                    profession_select = st.multiselect("Profession", profession_options, default=profile.get("profession", []))
                    expertise_select = st.multiselect("Expertise", expertise_options, default=profile.get("expertise", []))
                    
                    summary = st.text_area("Professional Summary", value=profile.get("summary", ""))
                    experience_text = st.text_area("Work Experience", value=profile.get("experience_text", ""))
                    education = st.text_area("Education", value=profile.get("education", ""))
                    skills = st.text_area("Skills (e.g., Python, SQL, HTML)", value=profile.get("skills", ""))

                    # Dynamic "Additional Information" block for editing
                    if "additional_info_list" not in st.session_state or st.session_state.profile_to_edit.get("id") != st.session_state.get("current_edit_profile_id"):
                        # FIX: Check if the retrieved data is a string and convert it to a list if needed.
                        additional_info_data = profile.get("additional_info", [""])
                        if isinstance(additional_info_data, str):
                            st.session_state.additional_info_list = [additional_info_data]
                        else:
                            # If it's a list (including an empty one), use it.
                            st.session_state.additional_info_list = additional_info_data
                        
                        st.session_state.current_edit_profile_id = profile.get("id")

                    st.write("Additional Information (e.g., Achievements, Certifications)")
                    for i, info in enumerate(st.session_state.additional_info_list):
                        st.session_state.additional_info_list[i] = st.text_input(
                            f"Info {i+1}", 
                            value=info,
                            key=f"add_info_edit_{i}",
                            label_visibility="collapsed"
                        )
                    if st.form_submit_button("Add another information block"):
                        st.session_state.additional_info_list.append("")
                        st.rerun()

                    submitted = st.form_submit_button("Update CV")
                    if submitted:
                        cleaned_additional_info = [item for item in st.session_state.additional_info_list if item.strip()]
                        if not any([name, contact, summary, experience_text, education, skills]) and not cleaned_additional_info:
                            st.warning("Please fill out at least one field to update your CV.")
                        else:
                            profile_data = {
                                "name": name,
                                "contact": contact,
                                "summary": summary,
                                "experience": experience_select,
                                "profession": profession_select,
                                "expertise": expertise_select,
                                "experience_text": experience_text,
                                "education": education,
                                "skills": skills,
                                "additional_info": cleaned_additional_info
                            }
                            save_profile(db, profile_data, user_id, doc_id=profile["id"])
                            st.session_state.edit_mode = False
                            st.session_state.profile_to_edit = {}
                            st.session_state.additional_info_list = [""] # Reset
                            st.rerun()
                
                if st.button("Cancel Edit"):
                    st.session_state.edit_mode = False
                    st.session_state.profile_to_edit = {}
                    st.session_state.additional_info_list = [""] # Reset
                    st.rerun()

        # --- Main Body Layout ---
        st.header("View All Profiles")
        st.markdown("Browse through the professional profiles created by others.")

        all_profiles = load_profiles(db)

        if all_profiles:
            group_by_option = st.selectbox(
                "Group Profiles by:", 
                ["None", "Experience", "Profession", "Expertise"]
            )
            
            if group_by_option == "None":
                for profile in all_profiles:
                    # Pass a static suffix for the key since there's no grouping
                    display_profile(profile, user_id, is_admin, key_suffix="no_grouping")
            else:
                grouped_profiles = {}
                for profile in all_profiles:
                    group_key = profile.get(group_by_option.lower(), ["Not specified"])
                    for key in group_key:
                        if key not in grouped_profiles:
                            grouped_profiles[key] = []
                        grouped_profiles[key].append(profile)
                
                for group_name, profiles_in_group in grouped_profiles.items():
                    st.subheader(f"Group: {group_name} ({len(profiles_in_group)})")
                    for profile in profiles_in_group:
                        # Pass the group name as the suffix to ensure a unique key for each button
                        display_profile(profile, user_id, is_admin, key_suffix=group_name)
        else:
            st.info("No profiles have been published yet. Be the first to create one!")
    else:
        st.error("The application cannot function without a successful database connection. Please check your configuration.")

if __name__ == "__main__":
    main()
