using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace RagSystem.Core.Entities;

[Table("chat_messages", Schema = "dotnet_app")]
public class ChatMessage
{
    [Key]
    public long Id { get; set; }

    public Guid ConversationId { get; set; }

    [Required]
    [MaxLength(20)]
    public string Role { get; set; } = string.Empty;

    public string Content { get; set; } = string.Empty;

    [Column(TypeName = "jsonb")]
    public List<Dictionary<string, object>>? Sources { get; set; }

    public double? ResponseTimeMs { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [ForeignKey("ConversationId")]
    public virtual Conversation Conversation { get; set; } = null!;
}
