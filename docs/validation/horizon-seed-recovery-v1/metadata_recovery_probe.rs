//! Exercise the real metadata recovery API only on an explicitly marked scratch copy.
use horizon_client_lib::save::{self, Level};
use std::{fs, path::PathBuf};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let world = PathBuf::from(std::env::args().nth(1).ok_or("copied QA world required")?);
    assert_eq!(
        fs::read_to_string(world.join(".qa-recovery-copy"))?,
        "TerraForged copied scratch world; safe to corrupt"
    );
    let current = world.join("level.dat");
    let old = world.join("level.dat_old");
    assert!(save::level_dat_issue(&world, false).is_none());
    assert!(save::level_dat_issue(&world, true).is_none());
    let valid_backup = fs::read(&old)?;
    let broken_current = b"QA deliberately invalid current metadata";
    let broken_backup = b"QA deliberately invalid backup metadata";
    fs::write(&current, broken_current)?;
    fs::write(&old, broken_backup)?;
    assert!(!save::fall_back_to_level_dat_old(&world));
    assert_eq!(fs::read(&current)?, broken_current);
    assert_eq!(fs::read(&old)?, broken_backup);
    fs::write(&old, &valid_backup)?;
    #[cfg(windows)]
    {
        use std::os::windows::fs::OpenOptionsExt;
        let lock = fs::OpenOptions::new().read(true).share_mode(0).open(&old)?;
        assert!(!save::restore_level_data_from_old(&world));
        drop(lock);
        assert_eq!(fs::read(&current)?, broken_current);
        assert_eq!(fs::read(&old)?, valid_backup);
    }
    assert!(save::level_data_needs_recovery(&world).is_some());
    assert!(save::fall_back_to_level_dat_old(&world));
    assert_eq!(fs::read(&current)?, valid_backup);
    assert!(save::level_dat_issue(&world, false).is_none());
    let mut preserved = false;
    for entry in fs::read_dir(&world)? {
        let entry = entry?;
        if entry
            .file_name()
            .to_string_lossy()
            .starts_with("level.dat_corrupted_")
        {
            preserved |= fs::read(entry.path())? == broken_current;
        }
    }
    assert!(preserved);
    let level = Level::read(&world).ok_or("recovered level unreadable")?;
    println!(
        "{}",
        serde_json::json!({"status":"passed-metadata-recovery-and-rollback","seed":level.seed,"windowsLockedBackupRollback":cfg!(windows),"corruptCurrentPreserved":true})
    );
    Ok(())
}
