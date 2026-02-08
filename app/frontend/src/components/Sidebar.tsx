interface SidebarProps {
  publishers: string[];
  selected: string;
  onSelect: (publisher: string) => void;
}

function Sidebar({ publishers, selected, onSelect }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-title">Publishers</div>
      <hr className="sidebar-divider" />
      {publishers.map((pub) => (
        <button
          key={pub}
          className={`sidebar-btn ${selected === pub ? 'active' : ''}`}
          onClick={() => onSelect(pub)}
        >
          {selected === pub ? '> ' : ''}{pub}
        </button>
      ))}
    </aside>
  );
}

export default Sidebar;
