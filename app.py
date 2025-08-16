import streamlit as st
from typing import List, Dict, Any, Optional
from collections import defaultdict

# Set page config
st.set_page_config(
    page_title="GitLab MR Comments Viewer",
    page_icon="🔍",
    layout="wide"
)

class GitLabMRCommentsApp:
    def __init__(self):
        self.session_state_keys = [
            'gitlab_url', 'project_id', 'private_token', 'mr_id_list', 
            'results_data', 'last_run_successful'
        ]
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Initialize session state variables"""
        defaults = {
            'gitlab_url': 'https://gitlab.com',
            'project_id': '56966359',
            'private_token': '',
            'mr_id_list': '',
            'results_data': [],
            'last_run_successful': False
        }
        
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    def get_all_merge_requests(self, gitlab_url: str, project_id: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Fetch all MRs with NashTech label"""
        mrs = []
        page = 1
        per_page = 50
        
        with st.spinner("Fetching merge requests..."):
            while True:
                url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests"
                params = {
                    "state": "all",
                    "labels": "NashTech",
                    "per_page": per_page,
                    "page": page
                }
                
                try:
                    resp = requests.get(url, headers=headers, params=params, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()
                    
                    if not data:
                        break
                    
                    mrs.extend(data)
                    if len(data) < per_page:
                        break
                    page += 1
                    
                except requests.exceptions.RequestException as e:
                    st.error(f"Error fetching merge requests: {e}")
                    return []
        
        return mrs

    def get_mr_by_ids(self, gitlab_url: str, project_id: str, headers: Dict[str, str], mr_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch MRs by specific IDs"""
        mrs = []
        
        with st.spinner(f"Fetching {len(mr_ids)} specific merge requests..."):
            for mr_id in mr_ids:
                url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_id}"
                try:
                    resp = requests.get(url, headers=headers, timeout=30)
                    resp.raise_for_status()
                    mrs.append(resp.json())
                except requests.exceptions.RequestException as e:
                    st.warning(f"Error fetching MR {mr_id}: {e}")
                    continue
        
        return mrs

    def get_mr_discussions(self, gitlab_url: str, project_id: str, headers: Dict[str, str], mr_iid: int) -> List[Dict[str, Any]]:
        """Fetch all discussions for an MR"""
        discussions = []
        page = 1
        per_page = 50
        
        while True:
            url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/discussions"
            params = {"per_page": per_page, "page": page}
            
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                
                if not data:
                    break
                
                discussions.extend(data)
                if len(data) < per_page:
                    break
                page += 1
                
            except requests.exceptions.RequestException as e:
                st.warning(f"Error fetching discussions for MR {mr_iid}: {e}")
                break
        
        return discussions

    def extract_code_snippet(self, gitlab_url: str, project_id: str, headers: Dict[str, str], note: Dict[str, Any], mr: Dict[str, Any]) -> str:
        """Extract code snippet from note position"""
        pos = note.get("position")
        if not pos or not pos.get("new_path"):
            return ""

        file_path_encoded = pos["new_path"].replace("/", "%2F")
        diff_url = f"{gitlab_url}/api/v4/projects/{project_id}/repository/files/{file_path_encoded}/raw"

        params = {"ref": pos.get("head_sha") or mr.get("sha")}
        try:
            resp = requests.get(diff_url, headers=headers, params=params, timeout=30)
            if resp.status_code == 200:
                file_content = resp.text.split("\n")
                start_line = pos.get("new_line") or pos.get("old_line")
                if start_line and 1 <= start_line <= len(file_content):
                    start = max(0, start_line - 2)
                    end = min(len(file_content), start_line + 1)
                    return "\n".join(file_content[start:end])
        except Exception:
            pass
        return ""

    def get_code_location_key(self, note: Dict[str, Any]) -> Optional[str]:
        """Generate a unique key for grouping comments by code location"""
        pos = note.get("position")
        if not pos:
            return None
        
        file_path = pos.get("new_path") or pos.get("old_path")
        line_number = pos.get("new_line") or pos.get("old_line")
        
        if file_path and line_number:
            return f"{file_path}:{line_number}"
        return None

    def group_comments_by_mr_and_code(self, results: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Group comments first by MR, then by code location within each MR"""
        mr_groups = defaultdict(lambda: defaultdict(list))
        
        for comment in results:
            mr_title = comment["MR Title"]
            location_key = comment.get("Code Location Key") or "general"
            mr_groups[mr_title][location_key].append(comment)
        
        return dict(mr_groups)

    def fetch_data(self, gitlab_url: str, project_id: str, private_token: str, mr_id_list: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Main function to fetch and process GitLab data"""
        headers = {"PRIVATE-TOKEN": private_token}
        results = []
        
        try:
            # Get MRs
            if mr_id_list:
                mrs = self.get_mr_by_ids(gitlab_url, project_id, headers, mr_id_list)
            else:
                mrs = self.get_all_merge_requests(gitlab_url, project_id, headers)
            
            if not mrs:
                st.warning("No merge requests found.")
                return []
            
            # Process each MR
            progress_bar = st.progress(0)
            total_mrs = len(mrs)
            
            for idx, mr in enumerate(mrs):
                mr_title = mr["title"]
                mr_iid = mr["iid"]
                
                st.text(f"Processing MR {idx + 1}/{total_mrs}: {mr_title}")
                
                discussions = self.get_mr_discussions(gitlab_url, project_id, headers, mr_iid)
                
                for discussion in discussions:
                    for note in discussion["notes"]:
                        if note["system"]:
                            continue  # Skip system notes
                        
                        code_snippet = self.extract_code_snippet(gitlab_url, project_id, headers, note, mr)
                        code_location_key = self.get_code_location_key(note)
                        
                        # Extract position details
                        pos = note.get("position", {})
                        file_path = pos.get("new_path") or pos.get("old_path") or ""
                        line_number = pos.get("new_line") or pos.get("old_line") or ""
                        
                        results.append({
                            "MR Title": mr_title,
                            "MR ID": mr_iid,
                            "Author": note['author']['name'],
                            "Created At": note.get('created_at', ''),
                            "Code Snippet": code_snippet.strip(),
                            "Review Comment": note["body"].strip(),
                            "Code Location Key": code_location_key,
                            "File Path": file_path,
                            "Line Number": line_number,
                            "Discussion ID": discussion.get("id", ""),
                            "Note ID": note.get("id", "")
                        })
                
                progress_bar.progress((idx + 1) / total_mrs)
            
            progress_bar.empty()
            st.success(f"Successfully processed {total_mrs} merge requests and found {len(results)} comments.")
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
            return []
        
        return results

    def generate_markdown_export(self, data: List[Dict[str, Any]]) -> str:
        """Generate markdown content for export with hierarchical grouping"""
        markdown_content = "# GitLab MR Comments Export\n\n"
        
        # Group by MR, then by code location
        grouped_data = self.group_comments_by_mr_and_code(data)
        
        for mr_title, code_locations in grouped_data.items():
            markdown_content += f"## MR: {mr_title}\n\n"
            
            # Get MR ID from first comment
            first_comment = next(iter(next(iter(code_locations.values()))))
            mr_id = first_comment['MR ID']
            markdown_content += f"**MR ID:** {mr_id}\n\n"
            
            for location_key, comments in code_locations.items():
                if location_key == "general":
                    markdown_content += "### General Comments\n\n"
                else:
                    file_path, line_num = location_key.split(":", 1)
                    markdown_content += f"### Code Location: {file_path}:{line_num}\n\n"
                    
                    # Show code snippet once for the location
                    if comments and comments[0]["Code Snippet"]:
                        markdown_content += f"```java\n{comments[0]['Code Snippet']}\n```\n\n"
                
                # Show all comments for this location
                for comment in comments:
                    markdown_content += f"**{comment['Author']}** at `{comment['Created At'][:19]}`:\n\n"
                    markdown_content += f"{comment['Review Comment']}\n\n"
                
                markdown_content += "---\n\n"
            
            markdown_content += "\n"
        
        return markdown_content

    def generate_csv_export(self, data: List[Dict[str, Any]]) -> str:
        """Generate CSV content for export"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["MR Title", "MR ID", "File Path", "Line Number", "Code Snippet", "Author", "Review Comment", "Created At"])
        
        # Write data
        for item in data:
            writer.writerow([
                item["MR Title"],
                item["MR ID"],
                item["File Path"],
                item["Line Number"],
                item["Code Snippet"],
                item["Author"],
                item["Review Comment"],
                item["Created At"]
            ])
        
        return output.getvalue()

    def render_ui(self):
        """Render the main UI"""
        st.title("🔍 GitLab MR Comments Viewer")
        st.markdown("Extract and view comments from GitLab Merge Requests with NashTech label")
        
        # Configuration section
        with st.expander("⚙️ Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                gitlab_url = st.text_input(
                    "GitLab URL",
                    value=st.session_state.gitlab_url,
                    help="The base URL of your GitLab instance"
                )
                
                project_id = st.text_input(
                    "Project ID",
                    value=st.session_state.project_id,
                    help="The GitLab project ID"
                )
            
            with col2:
                private_token = st.text_input(
                    "Private Token",
                    value=st.session_state.private_token,
                    type="password",
                    help="Your GitLab private access token"
                )
                
                mr_id_list = st.text_input(
                    "MR IDs (optional)",
                    value=st.session_state.mr_id_list,
                    help="Comma-separated list of MR IDs to filter (leave empty for all)"
                )
        
        # Parse MR ID list
        parsed_mr_ids = None
        if mr_id_list.strip():
            try:
                parsed_mr_ids = [int(x.strip()) for x in mr_id_list.split(',') if x.strip()]
                st.info(f"Will fetch specific MRs: {parsed_mr_ids}")
            except ValueError:
                st.error("Invalid MR ID format. Please use comma-separated numbers.")
                return
        
        # Run button
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            run_button = st.button("🚀 Run Analysis", type="primary")
        
        with col2:
            if st.session_state.results_data:
                st.button("🔄 Clear Results", on_click=lambda: st.session_state.update({'results_data': [], 'last_run_successful': False}))
        
        # Validation
        if run_button:
            if not all([gitlab_url, project_id, private_token]):
                st.error("Please fill in all required configuration fields.")
                return
            
            # Update session state
            st.session_state.update({
                'gitlab_url': gitlab_url,
                'project_id': project_id,
                'private_token': private_token,
                'mr_id_list': mr_id_list
            })
            
            # Fetch data
            with st.spinner("Fetching data from GitLab..."):
                results = self.fetch_data(gitlab_url, project_id, private_token, parsed_mr_ids)
                st.session_state.results_data = results
                st.session_state.last_run_successful = len(results) > 0
        
        # Display results
        if st.session_state.results_data:
            self.display_results(st.session_state.results_data)

    def display_results(self, data: List[Dict[str, Any]]):
        """Display the results grouped by MR, then by code location"""
        st.markdown("---")
        st.subheader("📊 Results")
        
        # Summary
        total_comments = len(data)
        unique_mrs = len(set(item["MR Title"] for item in data))
        
        # Calculate code location statistics
        grouped_data = self.group_comments_by_mr_and_code(data)
        total_code_locations = 0
        total_general_comments = 0
        
        for mr_title, code_locations in grouped_data.items():
            for location_key, comments in code_locations.items():
                if location_key == "general":
                    total_general_comments += len(comments)
                else:
                    total_code_locations += 1
        
        st.markdown(f"**Summary:** {total_comments} comments from {unique_mrs} merge requests")
        st.markdown(f"**Code Locations:** {total_code_locations} unique code locations, {total_general_comments} general comments")
        
        # Export buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            markdown_content = self.generate_markdown_export(data)
            st.download_button(
                label="📄 Export Markdown",
                data=markdown_content,
                file_name="gitlab_comments.md",
                mime="text/markdown"
            )
        
        with col2:
            csv_content = self.generate_csv_export(data)
            st.download_button(
                label="📊 Export CSV",
                data=csv_content,
                file_name="gitlab_comments.csv",
                mime="text/csv"
            )
        
        # Display hierarchical results
        self.display_hierarchical_results(data)

    def display_hierarchical_results(self, data: List[Dict[str, Any]]):
        """Display results with hierarchical grouping: MR -> Code Location -> Comments"""
        st.markdown("### Comments Grouped by MR and Code Location")
        
        grouped_data = self.group_comments_by_mr_and_code(data)
        
        # Create overview table
        overview_data = []
        for mr_title, code_locations in grouped_data.items():
            total_comments = sum(len(comments) for comments in code_locations.values())
            code_location_count = len([k for k in code_locations.keys() if k != "general"])
            general_comment_count = len(code_locations.get("general", []))
            
            # Get MR ID from first comment
            first_comment = next(iter(next(iter(code_locations.values()))))
            mr_id = first_comment['MR ID']
            
            overview_data.append({
                "MR Title": mr_title[:50] + "..." if len(mr_title) > 50 else mr_title,
                "MR ID": mr_id,
                "Total Comments": total_comments,
                "Code Locations": code_location_count,
                "General Comments": general_comment_count
            })
        
        df_overview = pd.DataFrame(overview_data)
        st.dataframe(df_overview, use_container_width=True)
        
        # Detailed hierarchical view
        st.markdown("### Detailed View")
        
        for mr_title, code_locations in grouped_data.items():
            total_mr_comments = sum(len(comments) for comments in code_locations.values())
            
            # Get MR ID from first comment
            first_comment = next(iter(next(iter(code_locations.values()))))
            mr_id = first_comment['MR ID']
            
            with st.expander(f"📋 MR: {mr_title} (ID: {mr_id}) - {total_mr_comments} comments", expanded=False):
                
                # Show code locations within this MR
                for location_key, comments in code_locations.items():
                    if location_key == "general":
                        st.markdown(f"#### 📝 General Comments ({len(comments)} comments)")
                    else:
                        file_path, line_num = location_key.split(":", 1)
                        st.markdown(f"#### 📍 {file_path}:{line_num} ({len(comments)} comments)")
                        
                        # Show code snippet once if available
                        if comments and comments[0]["Code Snippet"]:
                            st.markdown("**Code Snippet:**")
                            st.code(comments[0]["Code Snippet"], language="java")
                    
                    # Show all comments for this location
                    for i, comment in enumerate(comments):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**Comment {i+1} by {comment['Author']}**")
                        with col2:
                            st.markdown(f"*{comment['Created At'][:19]}*")
                        
                        st.markdown(comment["Review Comment"])
                        
                        if i < len(comments) - 1:
                            st.markdown("---")
                    
                    st.markdown("")  # Add space between code locations

def main():
    app = GitLabMRCommentsApp()
    app.render_ui()

if __name__ == "__main__":
    main()
