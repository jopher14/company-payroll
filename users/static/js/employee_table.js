const { useState, useMemo } = React;

function EmployeeTable({ employees }) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("full_name");
  const [sortDir, setSortDir] = useState("asc");
  const [page, setPage] = useState(1);
  const perPage = 10;

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    let rows = employees.filter(e =>
      (e.full_name || "").toLowerCase().includes(q) ||
      (e.role || "").toLowerCase().includes(q) ||
      (e.team || "").toLowerCase().includes(q) ||
      (e.status || "").toLowerCase().includes(q)
    );

    rows.sort((a, b) => {
      const A = (a[sortKey] || "").toLowerCase();
      const B = (b[sortKey] || "").toLowerCase();
      if (A < B) return sortDir === "asc" ? -1 : 1;
      if (A > B) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

    return rows;
  }, [employees, search, sortKey, sortDir]);

  const totalPages = Math.ceil(filtered.length / perPage);
  const shown = filtered.slice((page - 1) * perPage, page * perPage);

  function toggleSort(key) {
    if (key === sortKey) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  return (
    <div className="card shadow">
      <div className="card-body">

        <input
          type="text"
          className="form-control mb-3"
          placeholder="Search employees..."
          value={search}
          onChange={e => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />

        <div className="table-responsive">
          <table className="table table-hover align-middle">
            <thead className="table-dark">
              <tr>
                <th onClick={() => toggleSort("full_name")} style={{ cursor: "pointer" }}>
                  Name {sortKey==="full_name" ? (sortDir==="asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => toggleSort("role")} style={{ cursor: "pointer" }}>
                  Position {sortKey==="role" ? (sortDir==="asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => toggleSort("team")} style={{ cursor: "pointer" }}>
                  Team {sortKey==="team" ? (sortDir==="asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => toggleSort("status")} style={{ cursor: "pointer" }}>
                  Status {sortKey==="status" ? (sortDir==="asc" ? "▲" : "▼") : ""}
                </th>
              </tr>
            </thead>

            <tbody>
              {shown.length > 0 ? shown.map(emp => (
                <tr key={emp.id}>
                  <td>
                    <a
                      href={`/users/employees/update/${emp.id}/`}
                      className="fw-bold text-primary"
                      style={{ textDecoration: "none" }}
                    >
                      {emp.full_name}
                    </a>
                  </td>
                  <td>{emp.role}</td>

                  <td>
                    <span className={"badge " + (
                      !emp.team || emp.team === "No Team Assigned"
                      ? "bg-danger"
                      : "bg-success"
                    )}>
                      {emp.team || "No Team Assigned"}
                    </span>
                  </td>

                  <td>
                    <span className={"badge " + (
                      emp.status === "Active" ? "bg-success" : "bg-secondary"
                    )}>
                      {emp.status}
                    </span>
                  </td>
                </tr>
              )) : (
                <tr><td colSpan="4" className="text-center">No employees found.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="d-flex justify-content-between align-items-center">
          <div>Showing {shown.length} of {filtered.length}</div>
          <div className="btn-group">
            <button className="btn btn-outline-dark" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button>
            <button className="btn btn-outline-dark" disabled={page === totalPages} onClick={() => setPage(page + 1)}>Next</button>
          </div>
        </div>

      </div>
    </div>
  );
}

// Load Django JSON → React
const jsonData = JSON.parse(document.getElementById("employee-data").textContent);

ReactDOM.createRoot(document.getElementById("employee-react-table"))
  .render(<EmployeeTable employees={jsonData} />);
